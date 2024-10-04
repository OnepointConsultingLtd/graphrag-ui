from typing import List

from enum import Enum
from pathlib import Path

from urllib.parse import quote_plus, unquote_plus

from fasthtml.common import (
    FastHTML,
    picolink,
    Form,
    Label,
    Input,
    Hidden,
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
    HighlightJS,
)
from starlette.requests import Request

from graphrag_ui.service.graphrag_service import (
    list_projects,
    graphrag_init,
    graphrag_index,
    delete_project,
    get_project_dir,
    STATUS_MESSAGES,
)
from graphrag_ui.config import cfg
from graphrag_ui.ui.snippets import title_group, create_file_input

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
        MarkdownJS(),
        HighlightJS(langs=["python", "javascript", "html", "css"]),
    ),
    htmlkw={"data-theme": "dark"},
    ftrs=(footer,),
)

ID_UPLOAD_FORM = "upload-form"
ID_CONFIG_FORM = "config-form"
ID_CARD = "upload-card"
ID_SPINNER = "upload-spinner"
ID_INDEX_FORM = "index-form"
ID_PROJECT_DELETE_SPINNER = "project-delete-spinner"


REFRESH_LINK = (
    """<a href="javascript:window.location.reload(true)">Refresh to continue</a>"""
)


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
    rows = [
        Div(
            Div("Name", cls="grid-header"),
            Div("Status", cls="grid-header"),
            cls="grid-row",
        )
    ]
    for i, project in enumerate(projects):
        target_id = f"project_{i}"
        rows.append(
            Div(
                Div(
                    Form(
                        A(project.name, href=f"/project/{quote_plus(project.name)}"),
                        Div(
                            Div(
                                P("Deleting ..."),
                                cls="htmx-indicator",
                                id=ID_PROJECT_DELETE_SPINNER,
                            ),
                            Button(
                                "x",
                                hx_delete="/delete-project",
                                target_id=target_id,
                                hx_indicator=f"#{ID_PROJECT_DELETE_SPINNER}",
                                hx_swap="outerHTML",
                                cls="delete",
                                style="border-radius: 20px; border: 1px solid #ccc; line-height: 9px; text-indent: 0; padding: 7px 16px",
                            ),
                            style="display: flex;",
                        ),
                        Hidden(
                            id="projectName", name="projectName", value=project.name
                        ),
                        cls="grid-item",
                        style="display: flex; justify-content: space-between; align-items: center;",
                    )
                ),
                Div(STATUS_MESSAGES[project.status], cls="grid-item"),
                cls="grid-row",
                id=target_id,
            )
        )

    return Title(title), Main(
        H1(title),
        Div(
            A(
                Button("Create project", style="display: block; margin-left: auto;"),
                href="/create",
                style="display: block;",
            )
        ),
        Div(*rows, id="grid") if len(projects) > 0 else Div(P("No projects found. Create a new project to get started.", style="margin-top: 2em; ")),
        cls="container",
    )


@app.route("/create")
def get(session):
    file_amount = session.get("file_amount", 3)
    files = [create_file_input(number) for number in range(0, file_amount)]
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
        *files,
        Div(id="file-container"),
        Div(
            Button(
                " + ",
                style="margin-bottom: 20px; border-radius: 20px; border: 1px solid #ccc; padding: 3px 10px;",
                hx_post="/add-file",
                target_id="file-container",
                hx_swap="beforebegin",
            )
        ),
        Button("Create project"),
        Div(
            P("Uploading and creating project. Please wait ..."),
            cls="htmx-indicator",
            id=ID_SPINNER,
        ),
        hx_post="/myupload",
        hx_indicator=f"#{ID_SPINNER}",
        hx_swap="innerHTML",
        target_id=ID_CARD,
        id=ID_UPLOAD_FORM,
    )
    card = Div(id=ID_CARD, style="margin-top: 20px;")
    title = "Initialize Graph RAG Project"
    return Title(title), Main(title_group(title), project_form, card, cls="container")


@app.route("/add-file")
def post(session):
    file_amount = session.get("file_amount", 3)
    session["file_amount"] = file_amount + 1
    return create_file_input(file_amount)


@app.route("/delete-file")
def delete(session):
    file_amount = session.get("file_amount", 3)
    session["file_amount"] = file_amount - 1
    return ""


@app.route("/delete-project")
def delete(projectName: str):
    try:
        project_dir = get_project_dir(projectName)
        delete_project(project_dir)
        return ""
    except Exception as e:
        return f"Could not delete project {projectName}. Error: {e}"


@app.route("/myupload")
async def post(req: Request, projectTitle: str):
    async with req.form() as form:
        error_code = create_project(projectTitle)
        if error_code == ErrorCode.PROJECT_ALREADY_EXISTS:
            return f"Project {create_project_link(projectTitle)} already exists"

        files = []
        for k, v in form.items():
            if "myFile" in k:
                files.append(v)
        error_code = await init_graphrag_file(files, projectTitle)
        if error_code == ErrorCode.UNSUPPORTED_FILE_TYPE:
            return f"Unsupported file type. Only .txt files are supported."

        return f"""Project {create_project_link(projectTitle)} created successfully"""


@app.route("/project/index/{projectTitle}")
async def post(projectTitle: str):
    projectTitle = unquote_plus(projectTitle)
    project_dir = cfg.project_dir / projectTitle
    if not project_dir.exists():
        return f"Project {projectTitle} does not exist.<br />"
    try:
        graphrag_index(project_dir)
        return f"Project {projectTitle} indexed successfully. {REFRESH_LINK}<br />"
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


async def init_graphrag_file(files: List[UploadFile], project_title: str) -> ErrorCode:
    project_dir = Path(cfg.project_dir) / project_title

    invalid_files = 0
    for file in files:
        content_type = file.content_type
        file_name = file.filename
        if content_type in ["text/plain"]:
            input_file_path = project_dir / "input"
            input_file_path.mkdir(parents=True, exist_ok=True)
            file_path = input_file_path / file_name
            with file_path.open("wb") as f:
                content = await file.read()
                f.write(content)
        else:
            invalid_files += 1

    if invalid_files > 0:
        return ErrorCode.UNSUPPORTED_FILE_TYPE

    try:
        graphrag_init(project_dir)
    except Exception as e:
        print(e)
        return ErrorCode.GRAPHRAG_INIT_ERROR
    return ErrorCode.OK
