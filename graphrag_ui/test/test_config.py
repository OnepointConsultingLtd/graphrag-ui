import os
import pytest
from graphrag_ui.config import Config, cfg
from graphrag.query.llm.oai.chat_openai import ChatOpenAI
from graphrag.query.llm.oai.typing import OpenaiApiType


def test_config_initialization():
    assert isinstance(cfg, Config)


def test_openai_api_key():
    assert cfg.openai_api_key == os.getenv("OPENAI_API_KEY")


def test_open_ai_model():
    assert cfg.open_ai_model == os.getenv("OPENAI_API_MODEL")


def test_tiktocken_encoding():
    assert cfg.tiktocken_encoding == os.getenv("TIKTOCKEN_ENCODING")


def test_llm_instance():
    assert isinstance(cfg.llm, ChatOpenAI)
    assert cfg.llm.api_key == cfg.openai_api_key
    assert cfg.llm.model == cfg.open_ai_model
    assert cfg.llm.api_type == OpenaiApiType.OpenAI
    assert cfg.llm.max_retries == 20


@pytest.mark.parametrize(
    "env_var",
    [
        "OPENAI_API_KEY",
        "OPENAI_API_MODEL",
        "TIKTOCKEN_ENCODING",
        "COMMUNITY_LEVEL",
        "PROJECT_DIR",
    ],
)
def test_environment_variables(env_var):
    assert os.getenv(env_var) is not None, f"{env_var} is not set in the environment"


def test_config_singleton():
    new_config = Config()
    assert new_config is cfg, "Config should be a singleton"
