from fasthtml.common import Group, H1, A, Img


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
