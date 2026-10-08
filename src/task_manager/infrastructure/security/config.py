from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class TokenConfiguration:
    signing_key: str
    issuer: str
    audience: str

    @classmethod
    def from_environment(cls) -> TokenConfiguration:
        signing_key: str = os.environ.get("JWT_SIGNING_KEY", "")
        issuer: str = os.environ.get("JWT_ISSUER", "")
        audience: str = os.environ.get("JWT_AUDIENCE", "")
        if len(signing_key.encode("utf-8")) < 32 or not issuer or not audience:
            raise RuntimeError("JWT signing configuration is incomplete.")
        return cls(signing_key, issuer, audience)


def api_docs_enabled() -> bool:
    return os.environ.get("ENABLE_API_DOCS", "false").lower() == "true"
