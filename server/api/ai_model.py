"""AI Model API endpoints"""

from typing import Optional, List
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.db.database import get_db_session
from server.models.ai_model import AIModel, ModelSupplier
from server.services.ai_model_service import AIModelService

router = APIRouter(prefix="/api/ai-model", tags=["ai-model"])


# Pydantic schemas
class AIModelBase(BaseModel):
    name: str
    supplier: str
    model_type: int = 0
    base_model: str
    api_key: str
    api_domain: Optional[str] = None
    is_default: bool = False
    config_list: Optional[dict] = None
    protocol: int = 1
    enabled: bool = True


class AIModelCreate(AIModelBase):
    pass


class AIModelUpdate(BaseModel):
    name: Optional[str] = None
    supplier: Optional[str] = None
    model_type: Optional[int] = None
    base_model: Optional[str] = None
    api_key: Optional[str] = None
    api_domain: Optional[str] = None
    is_default: Optional[bool] = None
    config_list: Optional[dict] = None
    protocol: Optional[int] = None
    enabled: Optional[bool] = None


class AIModelResponse(AIModelBase):
    id: int
    api_key_encrypted: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AIModelTestRequest(BaseModel):
    api_key: str
    model: str
    supplier: str = "openai"
    api_domain: Optional[str] = None
    config_list: Optional[dict] = None


class AIModelTestResponse(BaseModel):
    success: bool
    message: str


def get_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


def mask_api_key(api_key: str) -> str:
    """Mask API key for display"""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]


@router.get("", response_model=List[dict])
def list_models(db: Session = Depends(get_db)):
    """List all AI models"""
    models = db.query(AIModel).order_by(AIModel.created_at.desc()).all()
    result = []
    for m in models:
        result.append({
            "id": m.id,
            "name": m.name,
            "supplier": m.supplier,
            "supplier_name": ModelSupplier.names().get(m.supplier, m.supplier),
            "model_type": m.model_type,
            "base_model": m.base_model,
            "api_key": mask_api_key(m.api_key_encrypted),
            "api_domain": m.api_domain,
            "is_default": m.is_default,
            "protocol": m.protocol,
            "enabled": m.enabled,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        })
    return result


@router.post("", response_model=dict)
def create_model(model: AIModelCreate, db: Session = Depends(get_db)):
    """Create a new AI model"""
    # Validate supplier
    if model.supplier not in ModelSupplier.values():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid supplier. Must be one of: {ModelSupplier.values()}"
        )

    # If setting as default, unset other defaults
    if model.is_default:
        db.query(AIModel).filter(AIModel.is_default == True).update({"is_default": False})

    # Create model
    db_model = AIModel(
        name=model.name,
        supplier=model.supplier,
        model_type=model.model_type,
        base_model=model.base_model,
        api_key_encrypted=model.api_key,
        api_domain=model.api_domain,
        is_default=model.is_default,
        config_list=json.dumps(model.config_list) if model.config_list else None,
        protocol=model.protocol,
        enabled=model.enabled,
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)

    return {"id": db_model.id, "message": "Model created successfully"}


@router.put("/{model_id}", response_model=dict)
def update_model(model_id: int, model: AIModelUpdate, db: Session = Depends(get_db)):
    """Update an AI model"""
    db_model = db.query(AIModel).filter(AIModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    # If setting as default, unset other defaults
    if model.is_default:
        db.query(AIModel).filter(AIModel.is_default == True, AIModel.id != model_id).update({"is_default": False})

    # Update fields
    update_data = model.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "api_key":
            # Only update api_key if it's non-empty (to preserve existing key when not changing)
            if value:
                setattr(db_model, "api_key_encrypted", value)
        elif field == "config_list" and value:
            setattr(db_model, "config_list", json.dumps(value))
        elif field != "api_key":
            setattr(db_model, field, value)

    db.commit()
    return {"message": "Model updated successfully"}


@router.delete("/{model_id}", response_model=dict)
def delete_model(model_id: int, db: Session = Depends(get_db)):
    """Delete an AI model"""
    db_model = db.query(AIModel).filter(AIModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    db.delete(db_model)
    db.commit()
    return {"message": "Model deleted successfully"}


@router.post("/{model_id}/default", response_model=dict)
def set_default_model(model_id: int, db: Session = Depends(get_db)):
    """Set a model as the default"""
    db_model = db.query(AIModel).filter(AIModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    # Unset all defaults
    db.query(AIModel).filter(AIModel.is_default == True).update({"is_default": False})

    # Set this one as default
    db_model.is_default = True
    db.commit()

    return {"message": "Model set as default successfully"}


@router.post("/test", response_model=AIModelTestResponse)
def test_model_connection(test_req: AIModelTestRequest):
    """Test connection to an AI model"""
    response = AIModelService.test_connection(
        api_key=test_req.api_key,
        model=test_req.model,
        supplier=test_req.supplier,
        api_domain=test_req.api_domain,
        extra_config=test_req.config_list
    )

    if response.success:
        return AIModelTestResponse(success=True, message="Connection successful!")
    else:
        return AIModelTestResponse(success=False, message=f"Connection failed: {response.error}")


@router.get("/suppliers", response_model=dict)
def list_suppliers():
    """List all supported AI model suppliers"""
    return {
        "suppliers": [
            {"value": v, "label": ModelSupplier.names().get(v, v)}
            for v in ModelSupplier.values()
        ]
    }
