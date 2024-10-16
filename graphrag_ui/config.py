from pathlib import Path
import os

from dotenv import load_dotenv
import tiktoken

from graphrag.query.llm.oai.chat_openai import ChatOpenAI
from graphrag.query.llm.oai.typing import OpenaiApiType

from neo4j import GraphDatabase

load_dotenv()


class Neo4JConfig:

    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(Neo4JConfig, cls).__new__(cls)
        return cls._instance

    neo4j_uri = os.getenv("NEO4J_URI")
    assert neo4j_uri is not None, "Please specify a Neo4J URL"
    neo4j_username = os.getenv("NEO4J_USERNAME")
    assert neo4j_username is not None, "Please specify a Neo4J user name"
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    assert neo4j_password is not None, "Please specify a Neo4J password"
    neo4j_database = os.getenv("NEO4J_DATABASE")
    assert neo4j_database is not None, "Please specify a Neo4J database"
    # Create a Neo4j driver
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))


class Config:

    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    openai_api_key = os.getenv("OPENAI_API_KEY")
    open_ai_model = os.getenv("OPENAI_API_MODEL")
    open_ai_model_embedding = os.getenv("OPENAI_API_MODEL_EMBEDDING")

    llm = ChatOpenAI(
        api_key=openai_api_key,
        model=open_ai_model,
        api_type=OpenaiApiType.OpenAI,  # OpenaiApiType.OpenAI or OpenaiApiType.AzureOpenAI
        max_retries=20,
    )

    tiktocken_encoding = os.getenv("TIKTOCKEN_ENCODING")
    token_encoder = tiktoken.get_encoding(tiktocken_encoding)

    project_dir = os.getenv("PROJECT_DIR")
    project_dir = Path(project_dir)

    image_path = os.getenv("IMAGE_PATH")
    image_path = Path(image_path)

    neo4j = Neo4JConfig()


cfg = Config()
