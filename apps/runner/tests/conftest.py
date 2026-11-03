import pytest
from playwright.async_api import async_playwright


@pytest.fixture
async def browser():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        yield b
        await b.close()


@pytest.fixture
async def page(browser):
    context = await browser.new_context()
    pg = await context.new_page()
    yield pg
    await context.close()
