"""
Simple security utilities for the coaching system
"""

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from ..database import db

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_coach(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated coach"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        coach_id: str = payload.get("sub")
        if coach_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Verify coach exists in database
    coach = await db.fetchrow(
        "SELECT * FROM coaches WHERE id = ? AND is_active = 1",
        coach_id
    )
    if coach is None:
        raise credentials_exception
    
    # Convert to dict manually for SQLite
    if coach:
        return {
            "id": coach[0],
            "name": coach[1], 
            "email": coach[2],
            "whatsapp_token": coach[3]
        }
    return None
