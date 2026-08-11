from pydantic import BaseModel, Field, field_validator


class ClientCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    is_active: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split())


class ClientCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return " ".join(value.strip().split()) if value is not None else None
