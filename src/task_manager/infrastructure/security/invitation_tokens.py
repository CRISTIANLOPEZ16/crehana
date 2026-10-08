import hashlib
import secrets


class SecureInvitationTokenService:
    def issue(self) -> tuple[str, bytes]:
        token: str = secrets.token_urlsafe(32)
        return token, self.digest(token)

    def digest(self, token: str) -> bytes:
        return hashlib.sha256(token.encode("utf-8")).digest()
