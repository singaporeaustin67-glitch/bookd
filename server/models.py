"""Pydantic request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    product: str = Field(min_length=3, max_length=2000)
    target_titles: list[str] = Field(default_factory=list)
    target_countries: list[str] = Field(default_factory=list)
    target_industries: list[str] = Field(default_factory=list)
    send: bool = False  # explicit opt-in: actually email people


class LeadIn(BaseModel):
    email: str
    first_name: str = ""
    last_name: str = ""
    title: str = ""
    company: str = ""
    domain: str = ""
    country: str = ""
    industry: str = ""


class ReplyIn(BaseModel):
    email_id: int | None = None
    from_email: str = ""
    body: str = Field(min_length=1)


class ContactIn(BaseModel):
    name: str = ""
    email: str
    product: str = ""


class KeyIn(BaseModel):
    provider: str = Field(min_length=2, max_length=20)
    api_key: str = Field(min_length=8, max_length=200)


class TierUpdate(BaseModel):
    tier: str = Field(min_length=3, max_length=20)
