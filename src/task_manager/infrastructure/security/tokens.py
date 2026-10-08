from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from task_manager.infrastructure.security.config import TokenConfiguration


class AccessTokenService:
    def __init__(self, configuration: TokenConfiguration) -> None:
        self._configuration = configuration

    def issue(self, user_id: UUID) -> str:
        issued_at: datetime = datetime.now(UTC)
        expires_at: datetime = issued_at + timedelta(minutes=30)
        return jwt.encode(
            {
                "sub": str(user_id),
                "iat": issued_at,
                "exp": expires_at,
                "iss": self._configuration.issuer,
                "aud": self._configuration.audience,
            },
            self._configuration.signing_key,
            algorithm="HS256",
        )

    def verify(self, access_token: str) -> UUID:
        claims: dict[str, object] = jwt.decode(
            access_token,
            self._configuration.signing_key,
            algorithms=["HS256"],
            issuer=self._configuration.issuer,
            audience=self._configuration.audience,
            options={"require": ["sub", "iat", "exp", "iss", "aud"]},
        )
        subject: object = claims.get("sub")
        if not isinstance(subject, str):
            raise jwt.InvalidTokenError("Invalid subject claim.")
        return UUID(subject)
