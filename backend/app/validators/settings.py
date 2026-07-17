from typing import Optional
from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    """
    What GET /settings returns. Deliberately does NOT include
    openai_key_ref or any BYOK-related field — those are handled by
    separate BYOK routes later in Chapter 6, and should never be
    exposed through this general settings response.
    """
    id: str
    name: str
    agent_name: Optional[str] = None
    plan: str
    vector_store_id: Optional[str] = None
    widget_config: Optional[dict] = None
    created_at: str


class SettingsUpdate(BaseModel):
    """
    Fields a business owner may change via PATCH /settings.
    All optional so partial updates work (only send what changed).

    Excluded on purpose:
    - system_prompt   -> belongs to the Prompt page (Ch.17), not here
    - plan            -> changes go through billing, not a plain PATCH
    - vector_store_id -> system-managed by knowledge base uploads (Ch.10)
    - BYOK fields     -> separate dedicated routes, later in Ch.6
    """
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    agent_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    widget_config: Optional[dict] = None
