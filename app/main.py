from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api import chat
from app.services.rag_engine import init_database
from app.services.graph_rag import init_graph_db
from contextlib import asynccontextmanager
from app.core.database import init_db
from app.core.rabbitmq import rabbitmq

from app.core.redis_conf import ws_manager
from fastapi_limiter import FastAPILimiter
import asyncio
from app.worker import main as worker_main

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_database()
    init_graph_db()
    await rabbitmq.connect()
    
    await ws_manager.connect_redis()
    if ws_manager.redis_client:
        await FastAPILimiter.init(ws_manager.redis_client)
    
    worker_task = asyncio.create_task(worker_main())
    
    yield
    
    worker_task.cancel()
    await rabbitmq.close()
    await ws_manager.close_redis()


app = FastAPI(title="AI Career Advisor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat.router, prefix="/api")
from app.api import upload
app.include_router(upload.router, prefix="/api")

from app.api.chat import websocket_chat_endpoint
@app.websocket("/ws/chat/{user_id}")
async def websocket_fallback(websocket: WebSocket, user_id: str):
    """Fallback route cho trường hợp proxy strip mất prefix /api"""
    await websocket_chat_endpoint(websocket, user_id)


@app.get("/")
def root():
    return {"message": "Server AI Backend đang hoạt động tốt!"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
