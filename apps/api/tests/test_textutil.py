from kame_core.sources.textutil import html_to_text


def test_html_to_text_strips_real_tags_and_unescapes_entities() -> None:
    text = html_to_text("<p>What You&#39;ll Do &amp; More</p>")

    assert text == "What You'll Do & More"


def test_html_to_text_handles_escaped_html_from_feeds() -> None:
    text = html_to_text(
        "&lt;h3&gt;What You&#39;ll Do&lt;/h3&gt;&lt;p&gt;Build &amp; ship&lt;/p&gt;"
    )

    assert text == "What You'll Do\n\nBuild & ship"
