from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher


class Argon2PasswordService:
    def __init__(self) -> None:
        self._password_hash = PasswordHash(
            (Argon2Hasher(time_cost=2, memory_cost=19 * 1024, parallelism=1),)
        )

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._password_hash.verify(password, password_hash)
