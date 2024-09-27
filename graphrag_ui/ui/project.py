from urllib.parse import quote_plus, unquote_plus

from fasthtml.common import (
    Form,
    Label,
    Input,
    Hidden,
    Button,
    Div,
    Title,
    Main,
    H2,
    P,
    Br,
    B,
    A,
    Img,
    Li,
    Ul,
    Pre,
)

from graphrag_ui.service.graphrag_service import (
    get_project_status,
    list_output_files,
    list_columns,
    ProjectStatus,
    STATUS_MESSAGES,
)
from graphrag_ui.service.graphrag_query import query_rag_global
from graphrag_ui.config import cfg
from graphrag_ui.ui.snippets import title_group
from graphrag_ui.ui.webapp import (
    app,
    ID_CARD,
    ID_CONFIG_FORM,
    ID_INDEX_FORM,
    ID_SPINNER,
)

ID_GLOBAL_SEARCH_FORM = "global-search-form"
ID_GLOBAL_SEARCH_RESULT = "global-search-result"


def global_search_form(projectTitle: str) -> Form:
    return Form(
        Label(
            "Global search query",
            Input(
                id="query",
                name="query",
                required=True,
                placeholder="Please enter your query, like 'What are the main topics?'",
            ),
        ),
        Hidden(value=projectTitle, id="projectTitle"),
        Div(
            Button("Search"),
            Button("Clear", type="reset", id="global-search-reset-button"),
            cls="search-form-buttons",
        ),
        Div(
            P("Performing global search. Please wait ..."),
            cls="htmx-indicator",
            id=ID_SPINNER,
        ),
        hx_post=f"/project/global-search",
        hx_indicator=f"#{ID_SPINNER}",
        target_id=ID_GLOBAL_SEARCH_RESULT,
        id=ID_GLOBAL_SEARCH_FORM,
    )


@app.route("/project/{projectTitle}")
def get(projectTitle: str):
    projectTitle = unquote_plus(projectTitle)
    title = f"Project {projectTitle}"
    project_dir = cfg.project_dir / projectTitle
    project_status = get_project_status(project_dir)
    form_components = []
    output_files_components = []
    if project_status == ProjectStatus.INITIALIZED:
        config_form = Form(
            Label(
                "API Key",
                Input(
                    id="key",
                    name="key",
                    required=True,
                    placeholder="Please enter the API key",
                ),
            ),
            Hidden(value=projectTitle, id="projectTitle"),
            Button("Save API key"),
            Div(P("Uploading..."), cls="htmx-indicator", id=ID_SPINNER),
            hx_post="/project/key",
            hx_indicator=f"#{ID_SPINNER}",
            target_id=ID_CARD,
            id=ID_CONFIG_FORM,
        )
        form_components.append(config_form)
    elif project_status == ProjectStatus.CONFIGURED:
        index_form = Form(
            Button("Index project"),
            Div(
                P("Indexing. Please wait. This may take a while ..."),
                cls="htmx-indicator",
                id=ID_SPINNER,
            ),
            hx_post=f"/project/index/{quote_plus(projectTitle)}",
            hx_indicator=f"#{ID_SPINNER}",
            target_id=ID_CARD,
            id=ID_INDEX_FORM,
        )
        form_components.append(index_form)
    elif project_status == ProjectStatus.INDEXED:
        output_files = list_output_files(project_dir)
        for output_file in output_files:
            output_files_components.append(
                Div(
                    A(
                        Img(src="/file-zipper-svgrepo-com.svg", width=20, height=20),
                        output_file.name,
                        href=f"/project/output/{quote_plus(projectTitle)}/{quote_plus(output_file.name)}",
                    )
                )
            )
        form_components.append(global_search_form(projectTitle))
    status = (Div(P("Status: ", B(STATUS_MESSAGES[project_status]))),)
    card = Div(id=ID_GLOBAL_SEARCH_RESULT, style="margin-top: 10px;", cls="marked")
    output_files_container = (
        Div(H2("Output files"), Div(*output_files_components, cls="grid-container-1-2"))
        if len(output_files_components) > 0
        else None
    )
    return Title(title), Main(
        title_group(title),
        status,
        *form_components,
        card,
        output_files_container,
        cls="container",
    )


@app.route("/project/global-search")
async def post(projectTitle: str, query: str):
    projectTitle = unquote_plus(projectTitle)
    results = await query_rag_global(query, cfg.project_dir / projectTitle)
    return results


@app.route("/project/output/{projectTitle}/{file_name}")
def post(projectTitle: str, file_name: str):
    projectTitle = unquote_plus(projectTitle)
    file_name = unquote_plus(file_name)
    file = cfg.project_dir / projectTitle / "output" / file_name
    columns, head = list_columns(file)
    title = f"File {file_name}"
    columns_components = []
    for column in columns:
        columns_components.append(Li(column))
    columns_list = Ul(*columns_components, cls="list-group")
    return Title(f"File {file_name}"), Main(
        title_group(title),
        Div(
            "Project: ", B(A(projectTitle, href=f"/project/{quote_plus(projectTitle)}"))
        ),
        Br(),
        columns_list,
        Br(),
        Pre(head),
        cls="container",
    )
