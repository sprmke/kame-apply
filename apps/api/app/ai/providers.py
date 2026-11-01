"""Provider registry, tier defaults, price estimates, and PydanticAI model construction.

Prices are USD micro-dollars per 1M tokens and are ESTIMATES for the budget guard, not billing.
Unknown models fall back to the provider's default price (deliberately on the high side).
"""

from dataclasses import dataclass

import anyio.to_thread
from pydantic_ai.models import Model

from app.core.errors import AppError

TIERS = ("bulk", "standard", "premium")


@dataclass(frozen=True)
class Spec:
    id: str
    label: str
    tier_models: dict[str, str]
    default_price: tuple[int, int]  # (input, output) micro-dollars per 1M tokens
    prices: dict[str, tuple[int, int]]
    needs_key: bool = True


PROVIDERS: dict[str, Spec] = {
    "gemini": Spec(
        "gemini",
        "Google Gemini",
        {
            "bulk": "gemini-3.5-flash-lite",
            "standard": "gemini-3.5-flash",
            "premium": "gemini-3.1-pro-preview",
        },
        (1_250_000, 10_000_000),
        {
            "gemini-3.5-flash-lite": (100_000, 400_000),
            "gemini-3.5-flash": (300_000, 2_500_000),
            "gemini-3.1-pro-preview": (1_250_000, 10_000_000),
        },
    ),
    "groq": Spec(
        "groq",
        "Groq",
        {
            "bulk": "openai/gpt-oss-20b",
            "standard": "openai/gpt-oss-120b",
            "premium": "openai/gpt-oss-120b",
        },
        (150_000, 600_000),
        {"openai/gpt-oss-20b": (75_000, 300_000), "openai/gpt-oss-120b": (150_000, 600_000)},
    ),
    "openai": Spec(
        "openai",
        "OpenAI",
        {"bulk": "gpt-4o-mini", "standard": "gpt-4o", "premium": "gpt-4o"},
        (2_500_000, 10_000_000),
        {"gpt-4o-mini": (150_000, 600_000), "gpt-4o": (2_500_000, 10_000_000)},
    ),
    "anthropic": Spec(
        "anthropic",
        "Anthropic",
        {"bulk": "claude-haiku-5-5", "standard": "claude-sonnet-5-5", "premium": "claude-opus-5-5"},
        (5_000_000, 25_000_000),
        {},
    ),
    "openrouter": Spec(
        "openrouter",
        "OpenRouter",
        {t: "meta-llama/llama-3.3-70b-instruct:free" for t in TIERS},
        (1_000_000, 3_000_000),
        {},
    ),
    "ollama": Spec(
        "ollama", "Ollama (local)", {t: "llama3.2" for t in TIERS}, (0, 0), {}, needs_key=False
    ),
}

OPENROUTER_URL = "https://openrouter.ai/api/v1"
OLLAMA_URL = "http://localhost:11434/v1"


def price(provider: str, model: str) -> tuple[int, int]:
    spec = PROVIDERS[provider]
    return spec.prices.get(model, spec.default_price)


def cost_micros(provider: str, model: str, input_tokens: int, output_tokens: int) -> int:
    p_in, p_out = price(provider, model)
    return (input_tokens * p_in + output_tokens * p_out) // 1_000_000


def validate_base_url(url: str, *, allow_private: bool) -> str:
    """User-supplied endpoints are an SSRF vector. Hosted deployments refuse anything that
    resolves to a non-global address (Ollama is for local or self-hosted use) and restrict ports.
    Re-run at call time (`revalidate_base_url`) because DNS can change after saving."""
    from app.core.ssrf import assert_public_http_url

    try:
        return assert_public_http_url(url, allow_private=allow_private).rstrip("/")
    except AppError as exc:
        raise AppError("invalid_base_url", exc.message, 422) from exc


async def revalidate_base_url(url: str, *, allow_private: bool) -> None:
    """Call-time check, run off the event loop because name resolution blocks."""
    await anyio.to_thread.run_sync(lambda: validate_base_url(url, allow_private=allow_private))


def build_model(provider: str, *, api_key: str | None, model: str, base_url: str | None) -> Model:
    """Construct a PydanticAI model. Imports are local so unused SDKs are never loaded."""
    if provider == "gemini":
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        return GoogleModel(model, provider=GoogleProvider(api_key=api_key))
    if provider == "groq":
        from pydantic_ai.models.groq import GroqModel
        from pydantic_ai.providers.groq import GroqProvider

        return GroqModel(model, provider=GroqProvider(api_key=api_key))
    if provider == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        return AnthropicModel(model, provider=AnthropicProvider(api_key=api_key))
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    if provider == "openai":
        return OpenAIChatModel(model, provider=OpenAIProvider(api_key=api_key))
    if provider == "openrouter":
        return OpenAIChatModel(
            model, provider=OpenAIProvider(base_url=OPENROUTER_URL, api_key=api_key)
        )
    if provider == "ollama":
        import httpx

        # A public URL must not be able to 302 us to an internal address.
        client = httpx.AsyncClient(follow_redirects=False, timeout=60)
        return OpenAIChatModel(
            model,
            provider=OpenAIProvider(
                base_url=base_url or OLLAMA_URL, api_key="ollama", http_client=client
            ),
        )
    raise AppError("unknown_provider", "Unknown provider", 422)
