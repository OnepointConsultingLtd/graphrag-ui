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
    Group,
    Small,
)

from graphrag_ui.service.graphrag_service import (
    list_output_files,
    list_columns,
    set_api_key,
    get_project_dir,
    activate_claims,
    graphrag_prompt_tuning,
    ProjectStatus,
    convert_to_csv,
    STATUS_MESSAGES,
)
from graphrag_ui.service.graphrag_query import query_rag, generate_questions, SearchType
from graphrag_ui.config import cfg
from graphrag_ui.ui.snippets import (
    title_group,
    create_project_title_status,
    REFRESH_LINK,
)
from graphrag_ui.ui.webapp import (
    app,
    ID_CONFIG_FORM,
    ID_INDEX_FORM,
    ID_SPINNER,
)
from graphrag_ui.ui.ids import (
    ID_GLOBAL_SEARCH_RESULT,
)
from graphrag_ui.ui.forms import (
    claims_form,
    prompt_tuning_form,
    search_form,
    generate_question_form,
    create_csv_conversion_form,
)

SESSION_ASKED_QUESTIONS = "asked_questions"


@app.route("/project/{projectTitle}")
def get(projectTitle: str):
    title, project_status, _, projectTitle = create_project_title_status(projectTitle)
    form_components = []
    status_group = []
    status = (Div(P("Status: ", B(STATUS_MESSAGES[project_status]))),)
    if project_status == ProjectStatus.INITIALIZED:
        config_form = Form(
            Label(
                "API Key",
                Div(
                    Input(
                        id="key",
                        name="key",
                        required=True,
                        placeholder="Please enter the API key",
                    ),
                    Small(
                        "You can find your API key at ",
                        A(
                            "https://platform.openai.com/account/api-keys",
                            target="_blank",
                        ),
                        ".",
                    ),
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
        status_group.append(status)
    elif project_status == ProjectStatus.CONFIGURED:
        index_form = Form(
            Button(
                "Index project",
                {
                    "onclick": f"""document.getElementById("{ID_GLOBAL_SEARCH_RESULT}").replaceChildren()"""
                },
            ),
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
        status_group.append(status)
    elif project_status == ProjectStatus.INDEXED:
        form_components.append(search_form(projectTitle))
        status_group.append(
            Group(
                status,
                A(
                    "Project details",
                    href=f"/project/details/{quote_plus(projectTitle)}",
                    style="text-align: right;",
                ),
            )
        )
    card = Div(id=ID_GLOBAL_SEARCH_RESULT, style="margin-top: 10px;", cls="marked")
    return Title(title), Main(
        title_group(title),
        *status_group,
        *form_components,
        card,
        cls="container",
    )


@app.route("/project/details/{projectTitle}")
def get(projectTitle: str):
    title, project_status, project_dir, projectTitle = create_project_title_status(
        projectTitle
    )
    output_files_components = []
    csv_conversion_form = []
    if project_status == ProjectStatus.INDEXED:
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
        output_files_container = (
            Div(
                H2("Output files"),
                Div(
                    *output_files_components,
                    cls="grid-container-1-2",
                ),
            )
            if len(output_files_components) > 0
            else None
        )
        csv_conversion_form.extend(create_csv_conversion_form(projectTitle))
    return Title(title), Main(
        title_group(title),
        output_files_container,
        *csv_conversion_form,
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
        return f"Prompt tuning for project <b>{projectTitle}</b> finished."
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


@app.route("/project/convert-to-csv")
async def post(projectTitle: str):
    try:
        convert_to_csv(cfg.project_dir / projectTitle)
        return f"CSV conversion for project <b>{projectTitle}</b> finished."
    except Exception as e:
        return f"Failed to convert to CSVs: {e}"
