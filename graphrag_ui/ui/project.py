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
    H3,
    P,
    Br,
    B,
    A,
    Img,
    Li,
    Ul,
    Pre,
    NotStr,
)

from graphrag_ui.service.graphrag_service import (
    get_project_status,
    list_output_files,
    list_columns,
    set_api_key,
    has_claims,
    get_project_dir,
    activate_claims,
    has_claims_flag,
    graphrag_prompt_tuning,
    ProjectStatus,
    STATUS_MESSAGES,
)
from graphrag_ui.service.graphrag_query import query_rag, generate_questions, SearchType
from graphrag_ui.config import cfg
from graphrag_ui.ui.snippets import title_group, REFRESH_LINK
from graphrag_ui.ui.webapp import (
    app,
    ID_CONFIG_FORM,
    ID_INDEX_FORM,
    ID_SPINNER,
)

ID_GLOBAL_SEARCH_FORM = "global-search-form"
ID_GLOBAL_SEARCH_RESULT = "global-search-result"
ID_GGENERATE_FORM = "generate-form"
ID_CLAIMS_SPINNER = "claims-form-spinner"
ID_CLAIMS_FORM = "claims-form"
ID_GENERATION_SPINNER = "generation-spinner"
ID_TUNING_SPINNER = "tuning-spinner"
ID_PROMPT_TUNING_FORM = "prompt-tuning-form"
SESSION_ASKED_QUESTIONS = "asked_questions"


def search_form(projectTitle: str) -> Form:
    searchType = (
        Div(
            Input(
                "Global",
                type="radio",
                id="search-type",
                name="searchType",
                value=SearchType.GLOBAL.value,
                checked=True,
            ),
            Input(
                "Local",
                type="radio",
                id="search-type",
                name="searchType",
                value=SearchType.LOCAL.value,
            ),
            cls="search-type",
        )
        if has_claims(get_project_dir(projectTitle))
        else Hidden(SearchType.GLOBAL.value, id="search-type", name="searchType")
    )
    return Form(
        searchType,
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
            P("Performing search. Please wait ..."),
            cls="htmx-indicator",
            id=ID_SPINNER,
        ),
        hx_post=f"/project/search",
        hx_indicator=f"#{ID_SPINNER}",
        target_id=ID_GLOBAL_SEARCH_RESULT,
        id=ID_GLOBAL_SEARCH_FORM,
    )


def generate_question_form(projectTitle: str, query: str) -> Form:
    return Form(
        Button("Generate other questions"),
        Div(
            P("Generating question. Please wait ..."),
            cls="htmx-indicator",
            id=ID_GENERATION_SPINNER,
        ),
        Hidden(value=projectTitle, id="projectTitle", name="projectTitle"),
        Hidden(value=query, id="query", name="query"),
        hx_post=f"/project/generate-question",
        hx_indicator=f"#{ID_GENERATION_SPINNER}",
        target_id=ID_GGENERATE_FORM,
        id=ID_GGENERATE_FORM,
    )


def claims_form(projectTitle: str) -> Form:
    does_have_claims = has_claims_flag(get_project_dir(projectTitle))
    return Form(
        Hidden(value=str(not does_have_claims), id="enabled", name="enabled"),
        Hidden(value=projectTitle, id="projectTitle", name="projectTitle"),
        Button(
            "Activate claims" if not does_have_claims else "Deactivate claims",
            style="margin-bottom: 10px;",
        ),
        Div(
            P("Updating claims flag. Please wait ..."),
            cls="htmx-indicator",
            id=ID_CLAIMS_SPINNER,
        ),
        hx_put=f"/project/activate-claims",
        hx_indicator=f"#{ID_CLAIMS_SPINNER}",
        target_id=ID_CLAIMS_FORM,
        id=ID_CLAIMS_FORM,
        style="margin-bottom: 10px;",
    )


def prompt_tuning_form(projectTitle: str) -> Form:
    return Form(
        Button("Prompt tuning"),
        Hidden(value=projectTitle, id="projectTitle"),
        Div(
            P("Tuning prompts automatically. Please wait ..."),
            cls="htmx-indicator",
            id=ID_TUNING_SPINNER,
        ),
        hx_put="/project/prompt-tuning",
        hx_indicator=f"#{ID_TUNING_SPINNER}",
        target_id=ID_GLOBAL_SEARCH_RESULT,
        id=ID_PROMPT_TUNING_FORM,
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
            target_id=ID_GLOBAL_SEARCH_RESULT,
            id=ID_CONFIG_FORM,
        )
        form_components.append(claims_form(projectTitle))
        form_components.append(config_form)
    elif project_status == ProjectStatus.CONFIGURED:
        index_form = Form(
            Button("Index project", {"onclick": f"""document.getElementById("{ID_GLOBAL_SEARCH_RESULT}").replaceChildren()"""}),
            Div(
                P("Indexing. Please wait. This may take a while ..."),
                cls="htmx-indicator",
                id=ID_SPINNER,
            ),
            hx_post=f"/project/index/{quote_plus(projectTitle)}",
            hx_indicator=f"#{ID_SPINNER}",
            target_id=ID_GLOBAL_SEARCH_RESULT,
            id=ID_INDEX_FORM,
        )
        form_components.append(claims_form(projectTitle))
        form_components.append(prompt_tuning_form(projectTitle))
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
        form_components.append(search_form(projectTitle))
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


@app.route("/project/key")
async def post(projectTitle: str, key: str):
    project_dir = get_project_dir(projectTitle)
    try:
        set_api_key(project_dir, key)
        return f"""Key for project <b>{projectTitle}</b> set successfully. {REFRESH_LINK}"""
    except Exception as e:
        return f"Failed to set key: {e}"


@app.route("/project/activate-claims")
async def put(projectTitle: str, enabled: str):
    project_dir = get_project_dir(projectTitle)
    try:
        activate_claims(project_dir, enabled.lower() == "true")
        return f"Claims for project <b>{projectTitle}</b> {"activated" if enabled.lower() == 'true' else "deactivated"}."
    except Exception as e:
        return f"Failed to activate claims: {e}"


@app.route("/project/prompt-tuning")
async def put(projectTitle: str):
    project_dir = get_project_dir(projectTitle)
    try:
        graphrag_prompt_tuning(project_dir)
        return f"Prompt tuning for project <b>{projectTitle}</b> finished. You can now index the project if you want."
    except Exception as e:
        return f"Failed to start prompt tuning: {e}"


@app.route("/project/search")
async def post(projectTitle: str, query: str, searchType: str):
    search_type = SearchType.GLOBAL if searchType == "global" else SearchType.LOCAL
    projectTitle = unquote_plus(projectTitle)
    results = await query_rag(query, cfg.project_dir / projectTitle, search_type)
    if search_type == SearchType.LOCAL:
        form = generate_question_form(projectTitle, query)
        return tuple((form, NotStr(results)))
    else:
        return results


@app.route("/project/generate-question")
async def post(projectTitle: str, query: str):
    question_history = [query]
    questions = await generate_questions(
        question_history, cfg.project_dir / projectTitle
    )
    return Div(
        H3("Questions"),
        *[
            P(
                B(
                    A(
                        q,
                        id=f"question-{i}",
                        href=f"javascript: replaceQuestions(document.getElementById('question-{i}').innerText)",
                    )
                )
            )
            for i, q in enumerate(questions)
        ],
    )


@app.route("/project/output/{projectTitle}/{file_name}")
def get(projectTitle: str, file_name: str):
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
