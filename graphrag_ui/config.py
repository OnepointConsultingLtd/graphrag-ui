from pathlib import Path
import os

from dotenv import load_dotenv
import tiktoken

from graphrag.query.llm.oai.chat_openai import ChatOpenAI
from graphrag.query.llm.oai.typing import OpenaiApiType

load_dotenv()


class Config:

    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    openai_api_key = os.getenv("OPENAI_API_KEY")
    open_ai_model = os.getenv("OPENAI_API_MODEL")

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


cfg = Config()
