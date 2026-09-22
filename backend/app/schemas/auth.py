from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserPublic


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    # bcrypt only uses the first 72 bytes; keep the API aligned with that limit
    # so hash and verify can never disagree on long passwords.
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
