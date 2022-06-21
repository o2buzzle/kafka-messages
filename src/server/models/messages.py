import json
from pydantic import BaseModel


class Message(BaseModel):
    sender_id: int
    recipient_id: int
    body: str


class ReturnStatus(BaseModel):
    status: str
    message: str
