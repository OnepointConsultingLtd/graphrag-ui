import time
from pathlib import Path

import pandas as pd

from graphrag_ui.config import cfg
from graphrag_ui.logger_factory import logger



def batched_import(
    statement: str, df: pd.DataFrame, batch_size: int = 1000
) -> int:
    """
    Imports a dataframe into Neo4j in batches to optimize performance and prevent
    memory overload for large datasets.

    Parameters:
    ----------
    statement : str
        The Cypher query to execute for each batch of data. This query should be
        constructed with placeholders for the data that will be UNWOUND.

    df : pd.DataFrame
        The dataframe to be imported into Neo4j, where each row represents a record.

    batch_size : int, optional, default=1000
        The number of rows to process in each batch. Adjust this size based on
        performance considerations for your system.

    Returns:
    -------
    total : int
        The total number of rows processed.
    """
    total = len(df)
    start_s = time.time()
    for start in range(0, total, batch_size):
        batch = df.iloc[start : min(start + batch_size, total)]
        result = cfg.neo4j.driver.execute_query(
            "UNWIND $rows AS value " + statement,
            rows=batch.to_dict("records"),
            database_=cfg.neo4j.neo4j_database,
        )
        logger.info(result.summary.counters)
    logger.info(f"{total} rows in { time.time() - start_s} s.")
    return total


def create_constraints():
    statements = """
create constraint chunk_id if not exists for (c:__Chunk__) require c.id is unique;
create constraint document_id if not exists for (d:__Document__) require d.id is unique;
create constraint entity_id if not exists for (c:__Community__) require c.community is unique;
create constraint entity_id if not exists for (e:__Entity__) require e.id is unique;
create constraint entity_title if not exists for (e:__Entity__) require e.name is unique;
create constraint entity_title if not exists for (e:__Covariate__) require e.title is unique;
create constraint related_id if not exists for ()-[rel:RELATED]->() require rel.id is unique;
""".split(
        ";"
    )

    for statement in statements:
        if len((statement or "").strip()) > 0:
            logger.info(statement)
            cfg.neo4j.driver.execute_query(statement)


def clear_db():
    queries = ["match (a) -[r] -> () delete a, r", "match (a) delete a"]
    for q in queries:
        cfg.neo4j.driver.execute_query(
            q,
            database_=cfg.neo4j.neo4j_database,
        )


def create_path(input_dir: Path, file: str):
    return input_dir / f"output/{file}.parquet"


def import_final_docs(input_dir: Path) -> int:
    df = pd.read_parquet(
        create_path(input_dir, "create_final_documents"), columns=["id", "title"]
    )
    statement = """
MERGE (d:__Document__ {id:value.id})
SET d += value {.title}
"""
    return batched_import(statement, df)


def import_text_units(input_dir: Path) -> int:
    df = pd.read_parquet(create_path(input_dir, "create_final_text_units"),
                          columns=["id","text","n_tokens","document_ids"])
    statement = """
MERGE (c:__Chunk__ {id:value.id})
SET c += value {.text, .n_tokens}
WITH c, value
UNWIND value.document_ids AS document
MATCH (d:__Document__ {id:document})
MERGE (c)-[:PART_OF]->(d)
"""
    return batched_import(statement, df)


def import_nodes(input_dir: Path) -> int:
    df = pd.read_parquet(create_path(input_dir, "create_final_entities"),
                            columns=["name","type","description","human_readable_id","id","description_embedding","text_unit_ids"])
    statement = """
MERGE (e:__Entity__ {id: value.id})
SET e += value {.human_readable_id, .description, name: replace(value.name, '"', '')}
WITH e, value
CALL db.create.setNodeVectorProperty(e, "description_embedding", value.description_embedding)
WITH e, value,
     CASE WHEN coalesce(value.type, "") = "" THEN [] ELSE [replace(value.type, '"', '')] END AS labels
FOREACH (label IN labels | SET e:`label`)
WITH e, value
UNWIND value.text_unit_ids AS text_unit
MATCH (c:__Chunk__ {id: text_unit})
MERGE (c)-[:HAS_ENTITY]->(e)
"""
    return batched_import(statement, df)

def import_relationships(input_dir: Path) -> int:
    df = pd.read_parquet(create_path(input_dir, "create_final_relationships"),
                         columns=["source","target","id","rank","weight","human_readable_id","description","text_unit_ids"])
    rel_statement = """
    MATCH (source:__Entity__ {name:replace(value.source,'"','')})
    MATCH (target:__Entity__ {name:replace(value.target,'"','')})
    // not necessary to merge on id as there is only one relationship per pair
    MERGE (source)-[rel:RELATED {id: value.id}]->(target)
    SET rel += value {.rank, .weight, .human_readable_id, .description, .text_unit_ids}
    RETURN count(*) as createdRels
"""
    return batched_import(rel_statement, df)


def import_communities(input_dir: Path) -> int:
    df = pd.read_parquet(create_path(input_dir, "create_final_communities"), 
                     columns=["id","level","title","text_unit_ids","relationship_ids"])
    statement = """
MERGE (c:__Community__ {community:value.id})
SET c += value {.level, .title}
/*
UNWIND value.text_unit_ids as text_unit_id
MATCH (t:__Chunk__ {id:text_unit_id})
MERGE (c)-[:HAS_CHUNK]->(t)
WITH distinct c, value
*/
WITH *
UNWIND value.relationship_ids as rel_id
MATCH (start:__Entity__)-[:RELATED {id:rel_id}]->(end:__Entity__)
MERGE (start)-[:IN_COMMUNITY]->(c)
MERGE (end)-[:IN_COMMUNITY]->(c)
RETURn count(distinct c) as createdCommunities
"""
    return batched_import(statement, df)


def import_community_reports(input_dir: Path) -> int:
    df = pd.read_parquet(create_path(input_dir, "create_final_community_reports"),
                               columns=["id","community","level","title","summary", "findings","rank","rank_explanation","full_content"])
    # import communities
    community_statement = """
MERGE (c:__Community__ {community:value.community})
SET c += value {.level, .title, .rank, .rank_explanation, .full_content, .summary}
WITH c, value
UNWIND range(0, size(value.findings)-1) AS finding_idx
WITH c, value, finding_idx, value.findings[finding_idx] as finding
MERGE (c)-[:HAS_FINDING]->(f:Finding {id:finding_idx})
SET f += finding
"""
    return batched_import(community_statement, df)


def import_covariates(input_dir: Path) -> int:
    covariates_file = create_path(input_dir, "create_final_covariates")
    if not covariates_file.exists():
        return 0
    df = pd.read_parquet(create_path(input_dir, "create_final_covariates"))
    # import covariates
    cov_statement = """
    MERGE (c:__Covariate__ {id: value.id})
    SET c += reduce(
        result = {}, 
        key IN keys(value) | 
        CASE key
            WHEN  "text_unit_id", "document_ids", "n_tokens"
            THEN result
            WHEN value[key] IS NULL OR value[key] = ""
            THEN result
            ELSE result{key: value[key]}
        END
    )
    WITH c, value
    MATCH (ch:__Chunk__ {id: value.text_unit_id})
    MERGE (ch)-[:HAS_COVARIATE]->(c)
"""
    return batched_import(cov_statement, df)


def generate_neo4j_entities(project_name: str):
    clear_db()
    create_constraints()
    path = Path(cfg.project_dir/project_name)
    if not path.exists():
        logger.error(f"{path} does not exist. Neo4J entities will not be generated.")
    imported_docs = import_final_docs(path)
    logger.info(f"Imported {imported_docs} documents.")
    imported_texts = import_text_units(path)
    logger.info(f"Imported {imported_texts} text units.")
    imported_nodes = import_nodes(path)
    logger.info(f"Imported {imported_nodes} nodes.")
    imported_rels = import_relationships(path)
    logger.info(f"Imported {imported_rels} relationships.")
    imported_communities = import_communities(path)
    logger.info(f"Imported {imported_communities} communities.")
    imported_community_reports = import_community_reports(path)
    logger.info(f"Imported {imported_community_reports} community reports.")
    imported_covariates = import_covariates(path)
    logger.info(f"Imported {imported_covariates} covariates.")


if __name__ == "__main__":
    generate_neo4j_entities("DWell Full")