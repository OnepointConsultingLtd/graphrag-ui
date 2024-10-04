from pathlib import Path
from fasthtml.common import (
    Form,
    Label,
    Input,
    Hidden,
    Button,
    Div,
    P,
)
from graphrag_ui.service.graphrag_query import SearchType
from graphrag_ui.service.graphrag_service import (
    has_claims,
    get_project_dir,
    has_claims_flag,
)
from graphrag_ui.ui.webapp import (
    ID_SPINNER,
)
from graphrag_ui.ui.ids import (
    ID_GLOBAL_SEARCH_FORM,
    ID_GLOBAL_SEARCH_RESULT,
    ID_GGENERATE_FORM,
    ID_CLAIMS_SPINNER,
    ID_CLAIMS_FORM,
    ID_GENERATION_SPINNER,
    ID_TUNING_SPINNER,
    ID_PROMPT_TUNING_FORM,
    ID_CONVERSION_SPINNER,
)


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


def create_csv_conversion_form(projectTitle: str) -> Form:
    project_dir = get_project_dir(projectTitle)
    results = []
    if not has_csv_files(project_dir):
        results.append(
            Div(
                Form(
                    Button("Convert parquet files to CSV"),
                    Hidden(value=projectTitle, id="projectTitle"),
                    Div(
                        P("Performing CSV conversion. Please wait ..."),
                        cls="htmx-indicator",
                        id=ID_CONVERSION_SPINNER,
                    ),
                    Div(
                        P(
                            "",
                            id="csv-conversion-result",
                            style="margin-top: -1em",
                        ),
                    ),
                    hx_post="/project/convert-to-csv",
                    hx_indicator=f"#{ID_CONVERSION_SPINNER}",
                    target_id="csv-conversion-result",
                    id=ID_PROMPT_TUNING_FORM,
                ),
                style="margin-top: 1em",
            )
        )
    return results


def has_csv_files(project_dir: Path) -> bool:
    return any((project_dir / "output").glob("*.csv"))
