from pydantic import BaseModel, Field, field_validator


class PinSetupRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=6)

    @field_validator("pin")
    @classmethod
    def pin_must_be_digits(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("PIN must contain only digits")
        return value


class PinVerifyRequest(BaseModel):
    pin: str


class PinStatusResponse(BaseModel):
    pin_is_set: bool
