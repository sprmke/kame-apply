"""Outbound email: SMTP (Mailpit locally) or Resend. Tests swap in the in-memory outbox."""

from dataclasses import dataclass
from email.message import EmailMessage

import aiosmtplib
import httpx
import structlog

from app.core.config import Settings

log = structlog.get_logger()


@dataclass(frozen=True)
class Mail:
    to: str
    subject: str
    text: str


class Mailer:
    def __init__(self, settings: Settings):
        self._s = settings

    async def send(self, mail: Mail) -> None:
        try:
            if self._s.resend_api_key:
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.post(
                        "https://api.resend.com/emails",
                        headers={"Authorization": f"Bearer {self._s.resend_api_key}"},
                        json={
                            "from": self._s.mail_from,
                            "to": [mail.to],
                            "subject": mail.subject,
                            "text": mail.text,
                        },
                    )
                    r.raise_for_status()
            else:
                msg = EmailMessage()
                msg["From"], msg["To"], msg["Subject"] = self._s.mail_from, mail.to, mail.subject
                msg.set_content(mail.text)
                await aiosmtplib.send(
                    msg, hostname=self._s.smtp_host, port=self._s.smtp_port, timeout=10
                )
        except Exception:
            # A mail outage must not fail sign-up or leak whether an address exists.
            log.exception("mail_send_failed", subject=mail.subject)


class Outbox(Mailer):
    """Test double: records mail instead of sending."""

    def __init__(self) -> None:
        self.sent: list[Mail] = []

    async def send(self, mail: Mail) -> None:
        self.sent.append(mail)
