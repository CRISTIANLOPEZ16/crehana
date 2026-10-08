from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, SecretStr, StringConstraints, field_validator
from typing import Annotated

from task_manager.infrastructure.http.schemas.common import StrictSchema


class RegisterAccountRequest(StrictSchema):
    display_name: Annotated[
        str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)
    ]
    email: EmailStr
    password: SecretStr

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, password: SecretStr) -> SecretStr:
        value: str = password.get_secret_value()
        if not 15 <= len(value) <= 128:
            raise ValueError("Must contain 15 to 128 Unicode characters.")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("Must contain valid Unicode text.") from error
        return password


class UserResponse(StrictSchema):
    id: UUID
    display_name: str
    email: str
    created_at: datetime
    updated_at: datetime


class AccessTokenResponse(StrictSchema):
    access_token: str
    token_type: str
    expires_in: int
