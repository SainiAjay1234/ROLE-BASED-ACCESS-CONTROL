from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory user store
USERS_DB = {
    "alice": {
        "username": "alice",
        "hashed_password": pwd_context.hash("alice123"),
        "role": "hr",
        "full_name": "Alice HR",
    },
    "bob": {
        "username": "bob",
        "hashed_password": pwd_context.hash("bob123"),
        "role": "finance",
        "full_name": "Bob Finance",
    },
    "charlie": {
        "username": "charlie",
        "hashed_password": pwd_context.hash("charlie123"),
        "role": "engineering",
        "full_name": "Charlie Eng",
    },
    "diana": {
        "username": "diana",
        "hashed_password": pwd_context.hash("diana123"),
        "role": "marketing",
        "full_name": "Diana Mkt",
    },
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123"),
        "role": "admin",
        "full_name": "System Admin",
    },
}


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(username: str, password: str):
    user = USERS_DB.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta=None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if username is None:
            return None
        return TokenData(username=username, role=role)
    except JWTError:
        return None