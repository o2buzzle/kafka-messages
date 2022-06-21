from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None


class User(BaseModel):
    username: str
    status: bool | None


class UserinDB(User):
    password: str