from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api import chat
from app.services.rag_engine import init_database
from contextlib import asynccontextmanager
from app.core.database import init_db
from app.core.rabbitmq import rabbitmq

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_database()
    await rabbitmq.connect()
    yield
    await rabbitmq.close()


app = FastAPI(title="AI Career Advisor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Server AI Backend đang hoạt động tốt!"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
