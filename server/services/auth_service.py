"""
Auth Service - JWT Authentication
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.orm import Session

from server.db.database import get_db_session


# JWT configuration - load from environment
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """
    JWT-based authentication service.

    Handles:
    - Password hashing and verification
    - JWT token generation and validation
    - User registration and login
    """

    def __init__(
        self,
        secret_key: str = JWT_SECRET_KEY,
        algorithm: str = JWT_ALGORITHM,
        expire_minutes: int = JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def hash_password(self, plain_password: str) -> str:
        """Hash a plain password using bcrypt."""
        return pwd_context.hash(plain_password)

    def verify_password(
        self,
        plain_password: str,
        hashed_password: str,
    ) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(
        self,
        user_id: int,
        username: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User ID to encode in token
            username: Username to encode in token
            expires_delta: Optional custom expiration time

        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.expire_minutes)

        payload = {
            "sub": str(user_id),
            "username": username,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload dict if valid, None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return payload
        except JWTError:
            return None

    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """Extract user_id from a valid token."""
        payload = self.verify_token(token)
        if payload:
            return int(payload.get("sub"))
        return None

    def register(
        self,
        db: Session,
        username: str,
        password: str,
        email: Optional[str] = None,
    ) -> dict:
        """
        Register a new user.

        Args:
            db: Database session
            username: Unique username
            password: Plain text password (will be hashed)
            email: Optional email

        Returns:
            dict with success status and user_id or error message
        """
        # Check if username exists
        check_query = text("SELECT id FROM users WHERE username = :username")
        existing = db.execute(check_query, {"username": username}).fetchone()
        if existing:
            return {
                "success": False,
                "error": "用户名已存在",
            }

        # Hash password and insert
        hashed = self.hash_password(password)
        insert_query = text("""
            INSERT INTO users (username, password_hash, email, created_at)
            VALUES (:username, :password_hash, :email, NOW())
            RETURNING id
        """)
        result = db.execute(insert_query, {
            "username": username,
            "password_hash": hashed,
            "email": email,
        })
        db.commit()
        user_id = result.fetchone()[0]

        return {
            "success": True,
            "user_id": user_id,
        }

    def authenticate(
        self,
        db: Session,
        username: str,
        password: str,
    ) -> Optional[dict]:
        """
        Authenticate user with username and password.

        Args:
            db: Database session
            username: Username
            password: Plain text password

        Returns:
            dict with user_id, username, access_token if successful, None otherwise
        """
        # Find user
        query = text("""
            SELECT id, username, password_hash, email
            FROM users
            WHERE username = :username
        """)
        result = db.execute(query, {"username": username})
        user = result.fetchone()

        if not user:
            return None

        user_id, username, password_hash, email = user

        # Verify password
        if not self.verify_password(password, password_hash):
            return None

        # Generate token
        token = self.create_access_token(user_id, username)

        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "access_token": token,
            "token_type": "bearer",
        }

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[dict]:
        """Get user info by ID."""
        query = text("""
            SELECT id, username, email, created_at
            FROM users
            WHERE id = :user_id
        """)
        result = db.execute(query, {"user_id": user_id})
        user = result.fetchone()

        if not user:
            return None

        return {
            "id": user[0],
            "username": user[1],
            "email": user[2],
            "created_at": user[3],
        }


# Singleton instance
_auth_service_instance: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get or create auth service singleton."""
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = AuthService()
    return _auth_service_instance
