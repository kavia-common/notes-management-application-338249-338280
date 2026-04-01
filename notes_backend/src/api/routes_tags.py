"""
Tags REST API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.db import get_db
from src.api.flows import tags_list_flow
from src.api.schemas import TagWithCountOut

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "",
    response_model=list[TagWithCountOut],
    summary="List tags",
    description="Return all tags with counts (number of notes using each tag), ordered by name.",
    operation_id="tags_list",
)
# PUBLIC_INTERFACE
def list_tags(db: Session = Depends(get_db)) -> list[TagWithCountOut]:
    """List tags with usage counts."""
    return tags_list_flow(db)
