from runner.extract import looks_like_captcha
from runner.live import map_pointer_to_page


def test_pointer_mapping_and_captcha_fixture():
    x, y = map_pointer_to_page(
        canvas_x=50, canvas_y=25, canvas_w=100, canvas_h=50, page_w=800, page_h=600
    )
    assert abs(x - 400) < 0.01 and abs(y - 300) < 0.01
    html = open("apps/runner/fixtures/captcha_like.html").read() if False else ""
    from pathlib import Path

    html = (Path(__file__).resolve().parents[1] / "fixtures" / "captcha_like.html").read_text()
    assert looks_like_captcha(html)
