"""
Reusable orchestration flows for notes/tags operations.

Flow names:
- NotesCreateFlow
- NotesUpdateFlow
- NotesDeleteFlow
- NotesListFlow
- NotesSearchFlow
- TagsListFlow
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.models import Note, Tag
from src.api.schemas import NoteCreate, NoteOut, NoteUpdate, TagWithCountOut

logger = logging.getLogger("notes_backend.flows")


def _normalize_tag_names(tag_names: Optional[Iterable[str]]) -> List[str]:
    if not tag_names:
        return []
    normalized: List[str] = []
    for t in tag_names:
        key = str(t or "").strip()
        if key:
            normalized.append(key)
    # deterministic ordering + de-dupe
    return sorted(set(normalized), key=lambda x: x.lower())


def _note_to_out(note: Note) -> NoteOut:
    return NoteOut(
        id=str(note.id),
        title=note.title,
        content=note.content,
        tags=sorted([t.name for t in note.tags], key=lambda x: x.lower()),
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def _get_or_create_tags(db: Session, tag_names: List[str]) -> List[Tag]:
    tags: List[Tag] = []
    for name in tag_names:
        existing = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if existing:
            tags.append(existing)
            continue

        created = Tag(name=name)
        db.add(created)
        try:
            db.flush()  # allocate id, validate uniqueness early
        except IntegrityError:
            db.rollback()
            # race/dup: re-read and continue
            existing2 = db.execute(select(Tag).where(Tag.name == name)).scalar_one()
            tags.append(existing2)
        else:
            tags.append(created)
    return tags


# PUBLIC_INTERFACE
def notes_list_flow(db: Session) -> List[NoteOut]:
    """NotesListFlow: list notes ordered by updated_at desc.

    Errors:
        - raises HTTPException(500) on unexpected DB issues.
    """
    logger.info("NotesListFlow start")
    try:
        notes = (
            db.execute(select(Note).order_by(Note.updated_at.desc(), Note.id.desc()))
            .scalars()
            .all()
        )
        out = [_note_to_out(n) for n in notes]
        logger.info("NotesListFlow success count=%s", len(out))
        return out
    except Exception as e:
        logger.exception("NotesListFlow failure")
        raise HTTPException(status_code=500, detail="Failed to list notes") from e


# PUBLIC_INTERFACE
def notes_search_flow(db: Session, query: str = "", tag: Optional[str] = None) -> List[NoteOut]:
    """NotesSearchFlow: search notes by query and optional tag.

    Contract:
        - `query` performs case-insensitive match on title/content and tag names.
        - `tag` filters by exact tag name (case-insensitive).

    Returns:
        List[NoteOut]: matching notes ordered by updated_at desc.
    """
    q = (query or "").strip()
    tag_key = (tag or "").strip()

    logger.info("NotesSearchFlow start query_len=%s tag=%s", len(q), tag_key or None)

    try:
        stmt = select(Note).distinct()

        if tag_key:
            stmt = stmt.join(Note.tags).where(func.lower(Tag.name) == tag_key.lower())

        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.outerjoin(Note.tags).where(
                func.lower(Note.title).like(like)
                | func.lower(Note.content).like(like)
                | func.lower(Tag.name).like(like)
            )

        stmt = stmt.order_by(Note.updated_at.desc(), Note.id.desc())

        notes = db.execute(stmt).scalars().all()
        out = [_note_to_out(n) for n in notes]
        logger.info("NotesSearchFlow success count=%s", len(out))
        return out
    except Exception as e:
        logger.exception("NotesSearchFlow failure")
        raise HTTPException(status_code=500, detail="Failed to search notes") from e


# PUBLIC_INTERFACE
def notes_create_flow(db: Session, draft: NoteCreate) -> NoteOut:
    """NotesCreateFlow: create a note with optional tags.

    Side effects:
        - inserts into notes table
        - creates tag rows as needed
        - creates note_tags associations
    """
    tag_names = _normalize_tag_names(draft.tags)

    logger.info("NotesCreateFlow start title_len=%s tags=%s", len(draft.title), tag_names)

    try:
        note = Note(title=draft.title.strip(), content=draft.content)
        if tag_names:
            note.tags = _get_or_create_tags(db, tag_names)

        db.add(note)
        db.commit()
        db.refresh(note)

        out = _note_to_out(note)
        logger.info("NotesCreateFlow success id=%s", out.id)
        return out
    except Exception as e:
        db.rollback()
        logger.exception("NotesCreateFlow failure")
        raise HTTPException(status_code=500, detail="Failed to create note") from e


# PUBLIC_INTERFACE
def notes_update_flow(db: Session, note_id: int, draft: NoteUpdate) -> NoteOut:
    """NotesUpdateFlow: update a note by id.

    Contract:
        - If draft.tags is provided, it *replaces* existing tags (after normalization).
        - If a field is omitted, it remains unchanged.
    """
    logger.info("NotesUpdateFlow start id=%s", note_id)

    try:
        note = db.execute(select(Note).where(Note.id == note_id)).scalar_one_or_none()
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        if draft.title is not None:
            note.title = draft.title.strip()
        if draft.content is not None:
            note.content = draft.content

        if draft.tags is not None:
            tag_names = _normalize_tag_names(draft.tags)
            note.tags = _get_or_create_tags(db, tag_names) if tag_names else []

        db.add(note)
        db.commit()
        db.refresh(note)

        out = _note_to_out(note)
        logger.info("NotesUpdateFlow success id=%s", out.id)
        return out
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("NotesUpdateFlow failure id=%s", note_id)
        raise HTTPException(status_code=500, detail="Failed to update note") from e


# PUBLIC_INTERFACE
def notes_delete_flow(db: Session, note_id: int) -> NoteOut:
    """NotesDeleteFlow: delete a note and return the deleted note."""
    logger.info("NotesDeleteFlow start id=%s", note_id)

    try:
        note = db.execute(select(Note).where(Note.id == note_id)).scalar_one_or_none()
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        out = _note_to_out(note)
        db.delete(note)
        db.commit()

        logger.info("NotesDeleteFlow success id=%s", out.id)
        return out
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("NotesDeleteFlow failure id=%s", note_id)
        raise HTTPException(status_code=500, detail="Failed to delete note") from e


# PUBLIC_INTERFACE
def tags_list_flow(db: Session) -> List[TagWithCountOut]:
    """TagsListFlow: list tags with note counts, ordered by name asc."""
    logger.info("TagsListFlow start")
    try:
        rows = db.execute(
            select(Tag.name, func.count(Note.id))
            .select_from(Tag)
            .join(Tag.notes, isouter=True)
            .group_by(Tag.id)
            .order_by(func.lower(Tag.name).asc())
        ).all()

        out = [TagWithCountOut(name=name, count=int(count or 0)) for (name, count) in rows]
        logger.info("TagsListFlow success count=%s", len(out))
        return out
    except Exception as e:
        logger.exception("TagsListFlow failure")
        raise HTTPException(status_code=500, detail="Failed to list tags") from e
