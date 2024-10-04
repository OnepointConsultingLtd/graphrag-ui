import shutil

from pathlib import Path
from enum import Enum
from typing import List, Tuple

import subprocess
import yaml

import pandas as pd

from graphrag_ui.config import cfg
from pydantic import BaseModel, Field

from graphrag_ui.service.graphrag_query import COVARIATE_TABLE


class ProjectStatus(Enum):
    NOT_INITIALIZED = 0
    INITIALIZED = 1
    CONFIGURED = 2
    INDEXED = 3
    UNKNOWN = 4


STATUS_MESSAGES = {
    ProjectStatus.NOT_INITIALIZED: "Project not initialized",
    ProjectStatus.INITIALIZED: "Project initialized",
    ProjectStatus.CONFIGURED: "Project configured",
    ProjectStatus.INDEXED: "Project indexed",
    ProjectStatus.UNKNOWN: "Project status unknown",
}


class Project(BaseModel):
    name: str = Field(..., description="The name of the project")
    status: ProjectStatus = Field(..., description="The status of the project")


def graphrag_init(input_dir: Path):
    subprocess.call(
        ["python", "-m", "graphrag.index", "--init", "--root", input_dir.as_posix()]
    )


def graphrag_index(input_dir: Path):
    # python -m graphrag.index --root $env:CONTENT_ROOT
    subprocess.call(["python", "-m", "graphrag.index", "--root", input_dir.as_posix()])


def graphrag_prompt_tuning(input_dir: Path):
    settings_file = input_dir / "settings.yaml"
    assert settings_file.exists(), "Settings file not found"
    subprocess.call(
        [
            "python",
            "-m",
            "graphrag.prompt_tune",
            "--root",
            input_dir.as_posix(),
            "--config",
            settings_file.as_posix(),
        ]
    )


def get_project_status(project_dir: Path) -> ProjectStatus:
    if not project_dir.exists():
        return ProjectStatus.NOT_INITIALIZED
    settings_file = project_dir / "settings.yaml"
    output_file = project_dir / "output"
    has_settings = settings_file.exists()
    if (
        has_settings
        and output_file.exists()
        and output_file.is_dir()
        and len(list(output_file.glob("*.parquet"))) > 0
    ):
        return ProjectStatus.INDEXED
    if has_settings:
        env_file = project_dir / ".env"
        if env_file.exists():
            with open(env_file, "r") as f:
                for line in f:
                    if line.startswith("GRAPHRAG_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        if api_key and api_key != "<API_KEY>":
                            return ProjectStatus.CONFIGURED
            return ProjectStatus.INITIALIZED
    return ProjectStatus.UNKNOWN


def set_api_key(project_dir: Path, api_key: str):
    env_file = project_dir / ".env"
    with open(env_file, "r") as f:
        lines = f.readlines()
    with open(env_file, "w") as f:
        for line in lines:
            if line.startswith("GRAPHRAG_API_KEY="):
                f.write(f"GRAPHRAG_API_KEY={api_key}\n")
            else:
                f.write(line)


def list_projects() -> List[Project]:
    return sorted(
        [
            Project(name=f.name, status=get_project_status(f))
            for f in cfg.project_dir.glob("*")
            if f.is_dir()
        ],
        key=lambda p: p.name.lower(),
    )


def list_output_files(project_dir: Path) -> List[Path]:
    return list((project_dir / "output").glob("*.parquet"))


def list_columns(file: Path) -> Tuple[List[str], str]:
    if file.suffix != ".parquet" or not file.exists():
        return []
    df = pd.read_parquet(file)
    head = df.head()
    return df.columns.values.tolist(), str(head)


def get_project_dir(projectTitle: str) -> Path:
    return cfg.project_dir / projectTitle


def has_claims(project_dir: Path) -> bool:
    return (project_dir / "output" / f"{COVARIATE_TABLE}.parquet").exists()


def has_claims_flag(project_dir: Path) -> bool:
    settings, _ = read_settings_yaml(project_dir)
    return settings["claim_extraction"] and "enabled" in settings["claim_extraction"]


def read_settings_yaml(project_dir: Path) -> dict:
    settings_file = project_dir / "settings.yaml"
    with open(settings_file, "r") as f:
        return yaml.safe_load(f), settings_file


def activate_claims(project_dir: Path, enabled: bool):
    settings, settings_file = read_settings_yaml(project_dir)
    settings["claim_extraction"]["enabled"] = enabled
    with open(settings_file, "w") as f:
        yaml.safe_dump(settings, f)


def delete_project(project_dir: Path):
    shutil.rmtree(project_dir)
