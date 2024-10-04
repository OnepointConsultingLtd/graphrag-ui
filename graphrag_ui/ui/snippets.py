from fasthtml.common import Group, H1, A, Img, Div, Input, Button


REFRESH_LINK = (
    """<a href="javascript:window.location.reload(true)">Refresh to continue</a>"""
)


def title_group(title: str):
    return Group(
        H1(title),
        A(
            Img(
                src="/house-svgrepo-com.svg",
                alt="Home",
                title="Home",
                width=24,
                height=24,
                style="margin-top: 0.5rem;",
            ),
            href="/",
            style="text-align: right;",
        ),
    )


def create_file_input(file_amount: int):
    id = f"file-container-{file_amount}"
    return Div(
        Input(id=f"myFile{file_amount}", type="file"),
        Button(
            "Delete",
            hx_delete="/delete-file",
            target_id=id,
            hx_swap="outerHTML",
            cls="delete",
        ),
        style="display: flex; align-items: center;",
        id=id,
    )
