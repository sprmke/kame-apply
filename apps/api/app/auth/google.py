"""Google OAuth 2.0 (authorization code + PKCE) via Authlib. Isolated behind a small class so
tests can substitute a fake; nothing else imports Authlib."""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

from authlib.integrations.httpx_client import AsyncOAuth2Client

from app.core.config import Settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


@dataclass(frozen=True)
class GoogleProfile:
    subject: str
    email: str
    email_verified: bool
    name: str | None


def new_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    return verifier, challenge.decode()


class GoogleOAuth:
    def __init__(self, settings: Settings):
        self._s = settings

    @property
    def configured(self) -> bool:
        return bool(self._s.google_client_id and self._s.google_client_secret)

    @property
    def redirect_uri(self) -> str:
        return f"{self._s.api_base_url.rstrip('/')}/api/v1/auth/google/callback"

    def authorization_url(self, *, state: str, code_challenge: str) -> str:
        params = {
            "client_id": self._s.google_client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    async def fetch_profile(self, *, code: str, verifier: str) -> GoogleProfile:
        client = AsyncOAuth2Client(
            client_id=self._s.google_client_id,
            client_secret=self._s.google_client_secret,
            redirect_uri=self.redirect_uri,
            timeout=15,
        )
        try:
            token = await client.fetch_token(TOKEN_URL, code=code, code_verifier=verifier)
            r = await client.get(  # pyright: ignore[reportAttributeAccessIssue]
                USERINFO_URL, headers={"Authorization": f"Bearer {token['access_token']}"}
            )
            r.raise_for_status()
            info = r.json()
        finally:
            await client.aclose()  # pyright: ignore[reportAttributeAccessIssue]
        return GoogleProfile(
            subject=str(info["sub"]),
            email=str(info["email"]).lower(),
            email_verified=bool(info.get("email_verified")),
            name=info.get("name"),
        )
