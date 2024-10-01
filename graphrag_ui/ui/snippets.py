from fasthtml.common import Group, H1, A, Img


REFRESH_LINK = """<a href="javascript:window.location.reload(true)">Refresh to continue</a>"""


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
