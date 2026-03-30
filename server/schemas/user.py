"""User schemas"""

from typing import Optional
from pydantic import BaseModel, EmailStr


class UserRegisterRequest(BaseModel):
    """User registration request."""
    username: str
    password: str
    email: Optional[str] = None


class UserLoginRequest(BaseModel):
    """User login request."""
    username: str
    password: str


class UserResponse(BaseModel):
    """User response."""
    id: int
    username: str
    email: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response with token."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
