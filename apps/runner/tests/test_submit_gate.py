"""The runner must never submit without an approved final_review.

These tests drive a real Chromium page: the earlier bug was that `input[type=submit]` sat in
`next_selectors` and was clicked on every loop iteration, submitting single-page forms with no
human decision.
"""

from pathlib import Path

from runner.adapters.base import Adapter, get_adapter
from runner.extract import page_has_captcha, page_has_password_input
from runner.fill import click_next, is_submit_like

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_submit_like_labels():
    assert is_submit_like("Submit")
    assert is_submit_like("Submit application")
    assert is_submit_like("Send application")
    assert is_submit_like("Apply now")
    assert not is_submit_like("Next")
    assert not is_submit_like("Continue")
    assert not is_submit_like("Save and Continue")


def test_no_adapter_uses_a_bare_submit_input_as_next():
    for key in ("greenhouse", "lever", "ashby", "workable", "workday", "generic"):
        adapter = get_adapter(key)
        assert "input[type=submit]" not in adapter.next_selectors


async def test_click_next_refuses_a_submit_only_form(page):
    await page.set_content(
        """
        <form onsubmit="window.submitted = true; return false;">
          <input id="email" name="email" type="email" />
          <input id="send" type="submit" value="Submit" />
        </form>
        """
    )
    assert await click_next(page, get_adapter("generic")) is False
    assert await page.evaluate("() => !!window.submitted") is False


async def test_click_next_still_clicks_a_next_input(page):
    await page.set_content(
        """
        <form onsubmit="window.submitted = true; return false;">
          <input id="email" name="email" type="email" />
          <input id="next" type="submit" value="Next" />
        </form>
        """
    )
    assert await click_next(page, get_adapter("generic")) is True
    assert await page.evaluate("() => !!window.submitted") is True


async def test_click_next_refuses_submit_button_with_continue_text(page):
    """A button whose label is Submit wins over a Next selector only if it is matched as next."""
    await page.set_content("<button>Submit application</button>")
    adapter = Adapter(key="x", host_needles=(), next_selectors=("button",))
    assert await click_next(page, adapter) is False


async def test_captcha_detection_ignores_a_script_tag(page):
    await page.set_content(
        """
        <h1>Apply at Acme</h1>
        <p>Read about our benefits.</p>
        <script src="https://www.google.com/recaptcha/api.js"></script>
        """
    )
    assert await page_has_captcha(page) is False


async def test_captcha_detection_sees_a_visible_challenge(page):
    await page.goto((FIXTURES / "captcha_like.html").as_uri())
    assert await page_has_captcha(page) is True


async def test_login_detection_requires_a_password_input(page):
    await page.set_content("<footer><a href='/login'>Sign in</a> · password help</footer>")
    assert await page_has_password_input(page) is False
    await page.goto((FIXTURES / "workday_login.html").as_uri())
    assert await page_has_password_input(page) is True
