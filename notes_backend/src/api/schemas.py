"""
API schemas for notes and tags.

Frontend expects notes shaped like:
{ id, title, content, tags?: string[], created_at?, updated_at? }

We expose id as a string to match the frontend normalization, even though the DB uses int.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    """Shared fields between note create/update and responses."""

    title: str = Field(..., min_length=1, max_length=200, description="Note title")
    content: str = Field(..., description="Note content (free text)")
    tags: Optional[List[str]] = Field(
        default=None,
        description="Optional list of tag names to associate with the note",
        examples=[["work", "ideas"]],
    )


class NoteCreate(NoteBase):
    """Request body for creating a note."""


class NoteUpdate(BaseModel):
    """Request body for updating a note (partial update via PUT in this API)."""

    title: Optional[str] = Field(
        default=None, min_length=1, max_length=200, description="Updated note title"
    )
    content: Optional[str] = Field(default=None, description="Updated note content")
    tags: Optional[List[str]] = Field(
        default=None,
        description="Updated tag list (replaces existing tags). Omit to keep unchanged.",
    )


class NoteOut(BaseModel):
    """Response model for a note."""

    id: str = Field(..., description="Note id (stringified integer)")
    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Note content")
    tags: List[str] = Field(default_factory=list, description="Associated tag names")
    created_at: datetime = Field(..., description="Creation timestamp (ISO 8601)")
    updated_at: datetime = Field(..., description="Last update timestamp (ISO 8601)")


class TagOut(BaseModel):
    """Response model for a tag."""

    name: str = Field(..., description="Tag name")


class TagWithCountOut(BaseModel):
    """Response model for tag listing with counts (useful for sidebar)."""

    name: str = Field(..., description="Tag name")
    count: int = Field(..., ge=0, description="Number of notes using this tag")
