import configparser
import sqlite3
from typing import Union
from datetime import datetime, timedelta

import aiosqlite
import fastapi
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from models.authentication import *
from passlib.context import CryptContext

configfile = configparser.ConfigParser()
configfile.read("config.ini")

SECRET_KEY = configfile["Server"]["SECRET_KEY"]
HASHING_ALGORITHM = "HS256"
EXPIRY_TIME = int(configfile["Server"]["ACCESS_TOKEN_EXPIRE_MINUTES"])
USERS_DATABASE = configfile["Server"]["USERS_DATABASE"]

router = fastapi.APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="authentication/login")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def get_user(username: str):
    async with aiosqlite.connect(USERS_DATABASE) as db:
        async with db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                user_data = {
                    "username": row[0],
                    "password": row[1],
                    "status": row[2],
                }
                return UserinDB(**user_data)
    return None


async def authenticate_user(username: str, password: str):
    user = await get_user(username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def generate_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=EXPIRY_TIME)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def get_current_user(token: str = fastapi.Depends(oauth2_scheme)):
    credentials_exception = fastapi.HTTPException(
        status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = await get_user(username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = fastapi.Depends(get_current_user),
):
    if current_user.status == True:
        return current_user
    else:
        raise fastapi.HTTPException(status_code=400, detail="Inactive user")


@router.post("/create_user")
async def create_user(username: str, password: str):
    async with aiosqlite.connect("users.db") as db:
        # Check if the user already exists
        async with db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ) as cursor:
            user = await cursor.fetchone()
            if user:
                return {"status": "error", "message": "user already exists"}
        # Create the user
        await db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, get_password_hash(password)),
        )
        await db.commit()
        return {"status": "ok", "message": "user created"}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = fastapi.Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise fastapi.HTTPException(
            status_code=400, detail="Incorrect username or password"
        )
    access_token = generate_token(
        data={"sub": user.username}, expires_delta=timedelta(minutes=EXPIRY_TIME)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=User)
async def read_users(current_user: User = fastapi.Depends(get_current_active_user)):
    return current_user
