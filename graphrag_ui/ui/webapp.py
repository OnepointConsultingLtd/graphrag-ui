from enum import Enum
from pathlib import Path

from urllib.parse import quote_plus, unquote_plus

from fasthtml.common import (
    FastHTML,
    picolink,
    Form,
    Label,
    Input,
    Button,
    Div,
    Title,
    Main,
    H1,
    H3,
    P,
    A,
    UploadFile,
    FileResponse,
    Script,
    Link,
    Dialog,
    MarkdownJS,
    HighlightJS
)

from graphrag_ui.service.graphrag_service import (
    list_projects,
    graphrag_init,
    graphrag_index,
    STATUS_MESSAGES,
)
from graphrag_ui.config import cfg
from graphrag_ui.ui.snippets import title_group

footer = Dialog(
    Div(
        H3("Error"),
        Div(id="dialog-content"),
        Div(id="dialog-status"),
        Button("Close", id="close-error-modal"),
    ),
    id="error-modal",
    cls="modal",
)

app = FastHTML(
    static_path=cfg.image_path,
    hdrs=(
        picolink,
        Link(href="/css/main.css", type="text/css", rel="stylesheet"),
        Script(src="/js/error.js"),
        Script(src="/js/main.js"),
        MarkdownJS(), HighlightJS(langs=['python', 'javascript', 'html', 'css'])
    ),
    ftrs=(footer,),
)

ID_UPLOAD_FORM = "upload-form"
ID_CONFIG_FORM = "config-form"
ID_CARD = "upload-card"
ID_SPINNER = "upload-spinner"
ID_INDEX_FORM = "index-form"


class ErrorCode(Enum):
    OK = 0
    PROJECT_ALREADY_EXISTS = 1
    UNSUPPORTED_FILE_TYPE = 2
    GRAPHRAG_INIT_ERROR = 3


@app.route("/{fname:path}.{ext:static}")
async def get(fname: str, ext: str):
    return FileResponse(f"assets/{fname}.{ext}")


@app.route("/")
def get():
    title = "Current projects"
    projects = list_projects()
    cells = [
        Div("Name", cls="grid-header"),
        Div("Status", cls="grid-header"),
    ]
    for project in projects:
        cells.append(
            Div(
                A(project.name, href=f"/project/{quote_plus(project.name)}"),
                cls="grid-item",
            )
        )
        cells.append(Div(STATUS_MESSAGES[project.status], cls="grid-item"))
    return Title(title), Main(
        H1(title),
        Div(
            A(
                Button("Create project", style="display: block; margin-left: auto;"),
                href="/create",
                style="display: block;",
            )
        ),
        Div(*cells, id="grid", cls="grid-container"),
        cls="container",
    )


@app.route("/create")
def get():
    project_form = Form(
        Label(
            "Project title",
            Input(
                id="projectTitle",
                name="projectTitle",
                placeholder="Please add the project title",
                required=True,
            ),
        ),
        Input(id="myFile", type="file"),
        Button("Create project"),
        Div(P("Uploading. Please wait ..."), cls="htmx-indicator", id=ID_SPINNER),
        hx_post="/myupload",
        hx_indicator=f"#{ID_SPINNER}",
        hx_swap="beforeend",
        target_id=ID_CARD,
        id=ID_UPLOAD_FORM,
    )
    card = Div(id=ID_CARD, style="margin-top: 20px;")
    title = "Initialize Graph RAG Project"
    return Title(title), Main(title_group(title), project_form, card, cls="container")


@app.route("/myupload")
async def post(myFile: UploadFile, projectTitle: str):
    error_code = create_project(projectTitle)
    if error_code == ErrorCode.PROJECT_ALREADY_EXISTS:
        return f"Project {create_project_link(projectTitle)} already exists"

    error_code = await init_graphrag_file(myFile, projectTitle)
    if error_code == ErrorCode.UNSUPPORTED_FILE_TYPE:
        return f"Unsupported file type {myFile.content_type}"

    print("My file", myFile)
    contents = await myFile.read()
    return f"""Project {create_project_link(projectTitle)} created successfully"""


@app.route("/project/index/{projectTitle}")
async def post(projectTitle: str):
    projectTitle = unquote_plus(projectTitle)
    project_dir = cfg.project_dir / projectTitle
    if not project_dir.exists():
        return f"Project {projectTitle} does not exist."
    try:
        graphrag_index(project_dir)
        return f"Project {projectTitle} indexed successfully."
    except Exception as e:
        return f"Error: {e}"


def create_project_link(projectTitle: str):
    return (
        f"""<b><a href="/project/{quote_plus(projectTitle)}">{projectTitle}</a></b>"""
    )


def create_project(project_title: str) -> ErrorCode:
    project_dir = Path(cfg.project_dir) / project_title
    if project_dir.exists():
        return ErrorCode.PROJECT_ALREADY_EXISTS
    project_dir.mkdir(parents=True)
    return ErrorCode.OK


async def init_graphrag_file(file: UploadFile, project_title: str) -> ErrorCode:
    content_type = file.content_type
    file_name = file.filename
    project_dir = Path(cfg.project_dir) / project_title

    if content_type in ["text/plain", "application/zip"]:
        input_file_path = project_dir / "input"
        input_file_path.mkdir(parents=True, exist_ok=True)
        file_path = input_file_path / file_name
        with file_path.open("wb") as f:
            content = await file.read()
            f.write(content)
        try:
            graphrag_init(project_dir)
        except Exception as e:
            print(e)
            return ErrorCode.GRAPHRAG_INIT_ERROR
        return ErrorCode.OK
    else:
        return ErrorCode.UNSUPPORTED_FILE_TYPE
