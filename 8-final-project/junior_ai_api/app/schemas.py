"""Pydantic v2 request / response schemas."""

from pydantic import BaseModel, Field, field_validator


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="The question to answer.")

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question must not be blank or whitespace only.")
        return v.strip()


class AnswerResponse(BaseModel):
    answer: str
