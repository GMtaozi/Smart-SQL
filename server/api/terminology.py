"""Terminology API endpoints"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.db.database import get_db_session
from server.api.auth import get_current_user_id
from server.models.terminology import Terminology

router = APIRouter(prefix="/api/terminology", tags=["terminology"])


class TerminologyBase(BaseModel):
    name: str
    term_type: Optional[str] = None
    datasource_id: Optional[int] = None
    synonyms: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True


class TerminologyCreate(TerminologyBase):
    pass


class TerminologyUpdate(BaseModel):
    name: Optional[str] = None
    term_type: Optional[str] = None
    datasource_id: Optional[int] = None
    synonyms: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class TerminologyResponse(TerminologyBase):
    id: int
    user_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


def get_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=List[TerminologyResponse])
def list_terminologies(
    datasource_id: Optional[int] = None,
    term_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all terminologies, optionally filtered by datasource or type"""
    query = db.query(Terminology)

    if datasource_id is not None:
        query = query.filter(
            (Terminology.datasource_id == datasource_id) |
            (Terminology.datasource_id == None)
        )

    if term_type:
        query = query.filter(Terminology.term_type == term_type)

    terminologies = query.order_by(Terminology.created_at.desc()).all()
    return [
        TerminologyResponse(
            id=t.id,
            user_id=t.user_id,
            name=t.name,
            term_type=t.term_type,
            datasource_id=t.datasource_id,
            synonyms=t.synonyms,
            description=t.description,
            enabled=t.enabled,
            created_at=t.created_at.isoformat() if t.created_at else None,
            updated_at=t.updated_at.isoformat() if t.updated_at else None,
        )
        for t in terminologies
    ]


@router.post("", response_model=dict)
def create_terminology(
    terminology: TerminologyCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new terminology entry"""
    db_term = Terminology(
        user_id=user_id,
        name=terminology.name,
        term_type=terminology.term_type,
        datasource_id=terminology.datasource_id,
        synonyms=terminology.synonyms,
        description=terminology.description,
        enabled=terminology.enabled,
    )
    db.add(db_term)
    db.commit()
    db.refresh(db_term)

    return {"id": db_term.id, "message": "Terminology created successfully"}


@router.put("/{term_id}", response_model=dict)
def update_terminology(
    term_id: int,
    terminology: TerminologyUpdate,
    db: Session = Depends(get_db)
):
    """Update a terminology entry"""
    db_term = db.query(Terminology).filter(Terminology.id == term_id).first()
    if not db_term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Terminology not found")

    update_data = terminology.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_term, field, value)

    db.commit()
    return {"message": "Terminology updated successfully"}


@router.delete("/{term_id}", response_model=dict)
def delete_terminology(term_id: int, db: Session = Depends(get_db)):
    """Delete a terminology entry"""
    db_term = db.query(Terminology).filter(Terminology.id == term_id).first()
    if not db_term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Terminology not found")

    db.delete(db_term)
    db.commit()
    return {"message": "Terminology deleted successfully"}


@router.get("/types", response_model=List[dict])
def list_term_types():
    """List all terminology types"""
    return [
        {"value": "GENERATE_SQL", "label": "SQL生成"},
        {"value": "ANALYSIS", "label": "数据分析"},
        {"value": "PREDICT", "label": "数据预测"},
    ]
