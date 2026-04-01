"""
Notes REST API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from src.api.db import get_db
from src.api.flows import (
    notes_create_flow,
    notes_delete_flow,
    notes_list_flow,
    notes_search_flow,
    notes_update_flow,
)
from src.api.schemas import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get(
    "",
    response_model=list[NoteOut],
    summary="List notes",
    description="Return all notes ordered by most recently updated first.",
    operation_id="notes_list",
)
# PUBLIC_INTERFACE
def list_notes(db: Session = Depends(get_db)) -> list[NoteOut]:
    """List notes.

    Returns:
        list[NoteOut]: notes ordered by updated_at desc.
    """
    return notes_list_flow(db)


@router.get(
    "/search",
    response_model=list[NoteOut],
    summary="Search notes",
    description="Search notes by query (title/content/tags) and/or filter by exact tag name.",
    operation_id="notes_search",
)
# PUBLIC_INTERFACE
def search_notes(
    q: str = Query(default="", description="Free-text query"),
    tag: str | None = Query(default=None, description="Filter by exact tag name"),
    db: Session = Depends(get_db),
) -> list[NoteOut]:
    """Search notes.

    Parameters:
        q: Optional query string.
        tag: Optional tag filter.
    """
    return notes_search_flow(db, query=q, tag=tag)


@router.post(
    "",
    response_model=NoteOut,
    summary="Create note",
    description="Create a new note with optional tags.",
    operation_id="notes_create",
)
# PUBLIC_INTERFACE
def create_note(draft: NoteCreate, db: Session = Depends(get_db)) -> NoteOut:
    """Create a note.

    Parameters:
        draft: NoteCreate body.

    Returns:
        NoteOut: the created note.
    """
    return notes_create_flow(db, draft)


@router.put(
    "/{note_id}",
    response_model=NoteOut,
    summary="Update note",
    description="Update an existing note. Fields omitted remain unchanged. If tags is provided it replaces existing tags.",
    operation_id="notes_update",
)
# PUBLIC_INTERFACE
def update_note(
    note_id: int = Path(..., ge=1, description="Note id"),
    draft: NoteUpdate = ...,
    db: Session = Depends(get_db),
) -> NoteOut:
    """Update a note by id."""
    return notes_update_flow(db, note_id=note_id, draft=draft)


@router.delete(
    "/{note_id}",
    response_model=NoteOut,
    summary="Delete note",
    description="Delete a note by id and return the deleted note.",
    operation_id="notes_delete",
)
# PUBLIC_INTERFACE
def delete_note(
    note_id: int = Path(..., ge=1, description="Note id"),
    db: Session = Depends(get_db),
) -> NoteOut:
    """Delete a note by id."""
    return notes_delete_flow(db, note_id=note_id)
