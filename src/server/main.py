import fastapi
from endpoints import messages

app = fastapi.FastAPI()

app.include_router(messages.router, prefix="/messages")
# app.include_router(authentication.router, prefix="/authentication")
