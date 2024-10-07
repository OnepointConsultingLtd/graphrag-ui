from typing import Union, List, Tuple

from enum import StrEnum
from pathlib import Path

from markdown import markdown
import pandas as pd
import tiktoken

from graphrag.query.llm.oai.embedding import OpenAIEmbedding
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_reports,
    read_indexer_relationships,
    read_indexer_covariates,
    read_indexer_text_units,
)
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.query.question_gen.local_gen import LocalQuestionGen, BaseQuestionGen
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)
from graphrag.vector_stores.lancedb import LanceDBVectorStore
from graphrag.query.input.loaders.dfs import (
    store_entity_semantic_embeddings,
)
from graphrag.query.structured_search.local_search.mixed_context import (
    LocalSearchMixedContext,
)
from graphrag.query.llm.oai.typing import OpenaiApiType

from graphrag_ui.config import cfg


COMMUNITY_REPORT_TABLE = "create_final_community_reports"
ENTITY_TABLE = "create_final_nodes"
ENTITY_EMBEDDING_TABLE = "create_final_entities"
RELATIONSHIP_TABLE = "create_final_relationships"
COVARIATE_TABLE = "create_final_covariates"
TEXT_UNIT_TABLE = "create_final_text_units"

# community level in the Leiden community hierarchy from which we will load the community reports
# higher value means we use reports from more fine-grained communities (at the cost of higher computation cost)
COMMUNITY_LEVEL = 2

token_encoder = tiktoken.get_encoding("cl100k_base")


class SearchType(StrEnum):
    GLOBAL = "global"
    LOCAL = "local"


def load_project_data(project_dir: Path):
    entity_df = pd.read_parquet(f"{project_dir}/output/{ENTITY_TABLE}.parquet")
    entity_embedding_df = pd.read_parquet(
        f"{project_dir}/output/{ENTITY_EMBEDDING_TABLE}.parquet"
    )
    report_df = pd.read_parquet(
        f"{project_dir}/output/{COMMUNITY_REPORT_TABLE}.parquet"
    )

    reports = read_indexer_reports(report_df, entity_df, COMMUNITY_LEVEL)
    entities = read_indexer_entities(entity_df, entity_embedding_df, COMMUNITY_LEVEL)

    return reports, entities


def get_claims(project_dir: Path) -> Union[dict, None]:
    file = f"{project_dir}/output/{COVARIATE_TABLE}.parquet"
    if Path(file).exists():
        covariate_df = pd.read_parquet(file)
        claims = read_indexer_covariates(covariate_df)
        covariates = {"claims": claims}
        return covariates
    return None


def build_local_context_builder(project_dir: Path) -> LocalSearchMixedContext:
    reports, entities = load_project_data(project_dir)

    # load description embeddings to an in-memory lancedb vectorstore
    # to connect to a remote db, specify url and port values.
    description_embedding_store = LanceDBVectorStore(
        collection_name="entity_description_embeddings",
    )
    lancedb_location = project_dir / "lancedb"
    description_embedding_store.connect(db_uri=lancedb_location)
    entity_description_embeddings = store_entity_semantic_embeddings(
        entities=entities, vectorstore=description_embedding_store
    )

    relationship_df = pd.read_parquet(
        f"{project_dir}/output/{RELATIONSHIP_TABLE}.parquet"
    )
    relationships = read_indexer_relationships(relationship_df)

    covariates = get_claims(project_dir)

    text_unit_df = pd.read_parquet(f"{project_dir}/output/{TEXT_UNIT_TABLE}.parquet")
    text_units = read_indexer_text_units(text_unit_df)

    text_embedder = OpenAIEmbedding(
        api_key=cfg.openai_api_key,
        api_base=None,
        api_type=OpenaiApiType.OpenAI,
        model=cfg.open_ai_model_embedding,
        deployment_name=cfg.open_ai_model_embedding,
        max_retries=20,
    )

    return LocalSearchMixedContext(
        community_reports=reports,
        text_units=text_units,
        entities=entities,
        relationships=relationships,
        # if you did not run covariates during indexing, set this to None
        covariates=covariates,
        entity_text_embeddings=description_embedding_store,
        embedding_vectorstore_key=EntityVectorStoreKey.ID,  # if the vectorstore uses entity title as ids, set this to EntityVectorStoreKey.TITLE
        text_embedder=text_embedder,
        token_encoder=token_encoder,
    )


def build_global_context_builder(project_dir: Path) -> GlobalCommunityContext:
    reports, entities = load_project_data(project_dir)

    return GlobalCommunityContext(
        community_reports=reports,
        entities=entities,  # default to None if you don't want to use community weights for ranking
        token_encoder=token_encoder,
    )


def init_local_params() -> Tuple[dict, dict]:
    local_context_params = {
        "text_unit_prop": 0.5,
        "community_prop": 0.1,
        "conversation_history_max_turns": 5,
        "conversation_history_user_turns_only": True,
        "top_k_mapped_entities": 10,
        "top_k_relationships": 10,
        "include_entity_rank": True,
        "include_relationship_weight": True,
        "include_community_rank": False,
        "return_candidate_context": False,
        "embedding_vectorstore_key": EntityVectorStoreKey.ID,  # set this to EntityVectorStoreKey.TITLE if the vectorstore uses entity title as ids
        "max_tokens": 12_000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
    }

    llm_params = {
        "max_tokens": 2_000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 1000=1500)
        "temperature": 0.0,
    }
    return (local_context_params, llm_params)


async def rag_local(query: str, project_dir: Path) -> str:

    context_builder = build_local_context_builder(project_dir)

    local_context_params, llm_params = init_local_params()

    # text_unit_prop: proportion of context window dedicated to related text units
    # community_prop: proportion of context window dedicated to community reports.
    # The remaining proportion is dedicated to entities and relationships. Sum of text_unit_prop and community_prop should be <= 1
    # conversation_history_max_turns: maximum number of turns to include in the conversation history.
    # conversation_history_user_turns_only: if True, only include user queries in the conversation history.
    # top_k_mapped_entities: number of related entities to retrieve from the entity description embedding store.
    # top_k_relationships: control the number of out-of-network relationships to pull into the context window.
    # include_entity_rank: if True, include the entity rank in the entity table in the context window. Default entity rank = node degree.
    # include_relationship_weight: if True, include the relationship weight in the context window.
    # include_community_rank: if True, include the community rank in the context window.
    # return_candidate_context: if True, return a set of dataframes containing all candidate entity/relationship/covariate records that
    # could be relevant. Note that not all of these records will be included in the context window. The "in_context" column in these
    # dataframes indicates whether the record is included in the context window.
    # max_tokens: maximum number of tokens to use for the context window.

    search_engine = LocalSearch(
        llm=cfg.llm,
        context_builder=context_builder,
        token_encoder=token_encoder,
        llm_params=llm_params,
        context_builder_params=local_context_params,
        response_type="multiple paragraphs",  # free form text describing the response type and format, can be anything, e.g. prioritized list, single paragraph, multiple paragraphs, multiple-page report
    )

    result = await search_engine.asearch(query)
    return markdown(result.response)


async def rag_global(query: str, project_dir: Path) -> str:

    context_builder = build_global_context_builder(project_dir)

    context_builder_params = {
        "use_community_summary": False,  # False means using full community reports. True means using community short summaries.
        "shuffle_data": True,
        "include_community_rank": True,
        "min_community_rank": 0,
        "community_rank_name": "rank",
        "include_community_weight": True,
        "community_weight_name": "occurrence weight",
        "normalize_community_weight": True,
        "max_tokens": 12_000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
        "context_name": "Reports",
    }

    map_llm_params = {
        "max_tokens": 1000,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    reduce_llm_params = {
        "max_tokens": 2000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 1000-1500)
        "temperature": 0.0,
    }

    search_engine = GlobalSearch(
        llm=cfg.llm,
        context_builder=context_builder,
        token_encoder=token_encoder,
        max_data_tokens=12_000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
        map_llm_params=map_llm_params,
        reduce_llm_params=reduce_llm_params,
        allow_general_knowledge=False,  # set this to True will add instruction to encourage the LLM to incorporate general knowledge in the response, which may increase hallucinations, but could be useful in some use cases.
        json_mode=True,  # set this to False if your LLM model does not support JSON mode.
        context_builder_params=context_builder_params,
        concurrent_coroutines=32,
        response_type="multiple paragraphs",  # free form text describing the response type and format, can be anything, e.g. prioritized list, single paragraph, multiple paragraphs, multiple-page report
    )

    result = await search_engine.asearch(query)
    return markdown(result.response)


async def generate_questions(
    question_history: List[str], project_dir: Path
) -> List[str]:

    context_builder = build_local_context_builder(project_dir)

    local_context_params, llm_params = init_local_params()

    question_generator = LocalQuestionGen(
        llm=cfg.llm,
        context_builder=context_builder,
        token_encoder=token_encoder,
        llm_params=llm_params,
        context_builder_params=local_context_params,
    )
    return await execute_question_generation(question_history, question_generator)


async def execute_question_generation(
    question_history: List[str], question_generator: BaseQuestionGen
) -> List[str]:
    candidate_questions = await question_generator.agenerate(
        question_history=question_history, context_data=None, question_count=5
    )
    return candidate_questions.response


async def query_rag(query: str, project_dir: Path, search_type: SearchType) -> str:
    match search_type:
        case SearchType.GLOBAL:
            return await rag_global(query, project_dir)
        case SearchType.LOCAL:
            return await rag_local(query, project_dir)
        case _:
            raise ValueError(f"Invalid search type: {search_type}")
