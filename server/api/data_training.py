"""Data Training API endpoints - SQL examples management"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.db.database import get_db_session
from server.api.auth import get_current_user_id
from server.models.data_training import DataTraining

router = APIRouter(prefix="/api/training", tags=["data-training"])


class DataTrainingBase(BaseModel):
    question: str
    sql: str
    datasource_id: Optional[int] = None
    description: Optional[str] = None
    enabled: bool = True


class DataTrainingCreate(DataTrainingBase):
    pass


class DataTrainingUpdate(BaseModel):
    question: Optional[str] = None
    sql: Optional[str] = None
    datasource_id: Optional[int] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class DataTrainingResponse(DataTrainingBase):
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


@router.get("", response_model=List[DataTrainingResponse])
def list_training_data(
    datasource_id: Optional[int] = None,
    enabled: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """List all training data, optionally filtered"""
    query = db.query(DataTraining)

    if datasource_id is not None:
        query = query.filter(
            (DataTraining.datasource_id == datasource_id) |
            (DataTraining.datasource_id == None)
        )

    if enabled is not None:
        query = query.filter(DataTraining.enabled == enabled)

    offset = (page - 1) * page_size
    training_data = query.order_by(DataTraining.created_at.desc()).offset(offset).limit(page_size).all()

    return [
        DataTrainingResponse(
            id=t.id,
            user_id=t.user_id,
            question=t.question,
            sql=t.sql,
            datasource_id=t.datasource_id,
            description=t.description,
            enabled=t.enabled,
            created_at=t.created_at.isoformat() if t.created_at else None,
            updated_at=t.updated_at.isoformat() if t.updated_at else None,
        )
        for t in training_data
    ]


@router.post("", response_model=dict)
def create_training_data(
    training: DataTrainingCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new training data entry"""
    db_training = DataTraining(
        user_id=user_id,
        question=training.question,
        sql=training.sql,
        datasource_id=training.datasource_id,
        description=training.description,
        enabled=training.enabled,
    )
    db.add(db_training)
    db.commit()
    db.refresh(db_training)

    return {"id": db_training.id, "message": "Training data created successfully"}


@router.put("/{training_id}", response_model=dict)
def update_training_data(
    training_id: int,
    training: DataTrainingUpdate,
    db: Session = Depends(get_db)
):
    """Update a training data entry"""
    db_training = db.query(DataTraining).filter(DataTraining.id == training_id).first()
    if not db_training:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training data not found")

    update_data = training.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_training, field, value)

    db.commit()
    return {"message": "Training data updated successfully"}


@router.delete("/{training_id}", response_model=dict)
def delete_training_data(training_id: int, db: Session = Depends(get_db)):
    """Delete a training data entry"""
    db_training = db.query(DataTraining).filter(DataTraining.id == training_id).first()
    if not db_training:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training data not found")

    db.delete(db_training)
    db.commit()
    return {"message": "Training data deleted successfully"}


@router.post("/batch-delete", response_model=dict)
def batch_delete_training_data(
    ids: List[int],
    db: Session = Depends(get_db)
):
    """Batch delete training data"""
    if not ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No IDs provided")

    db.query(DataTraining).filter(DataTraining.id.in_(ids)).delete(synchronize_session=False)
    db.commit()

    return {"message": f"Deleted {len(ids)} items successfully"}
