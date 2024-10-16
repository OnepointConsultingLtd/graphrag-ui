from pathlib import Path
from graphrag.index.cli import index_cli
from graphrag.index.progress.types import ReporterType

base = Path("/tmp/graphrag-ui/DWell Full")

index_cli(
    base.as_posix(),
    init=True,
    verbose=True,
    resume="",
    update_index_id=None,
    memprofile=False,
    nocache=False,
    reporter=ReporterType.RICH,
    config_filepath="settings.xml",
    emit="parquet,csv",
    dryrun=False,
    skip_validations=False,
    output_dir=(base / "output").as_posix(),
)
