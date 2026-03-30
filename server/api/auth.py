"""Authentication API routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from server.db.database import get_db_session
from server.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    LoginResponse,
    UserResponse,
)
from server.services.auth_service import get_auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """Dependency to get current user ID from JWT token."""
    token = credentials.credentials
    auth_service = get_auth_service()
    user_id = auth_service.get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        )
    return user_id


@router.post("/register", response_model=dict)
def register(request: UserRegisterRequest):
    """Register a new user."""
    auth_service = get_auth_service()
    db = get_db_session()
    try:
        result = auth_service.register(
            db,
            username=request.username,
            password=request.password,
            email=request.email,
        )
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"],
            )
        return {"success": True, "user_id": result["user_id"]}
    finally:
        db.close()


@router.post("/login", response_model=LoginResponse)
def login(request: UserLoginRequest):
    """Login and get access token."""
    auth_service = get_auth_service()
    db = get_db_session()
    try:
        result = auth_service.authenticate(
            db,
            username=request.username,
            password=request.password,
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )
        return LoginResponse(**result)
    finally:
        db.close()


@router.get("/me", response_model=UserResponse)
def get_current_user(user_id: int = Depends(get_current_user_id)):
    """Get current user info."""
    auth_service = get_auth_service()
    db = get_db_session()
    try:
        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )
        return UserResponse(**user)
    finally:
        db.close()
