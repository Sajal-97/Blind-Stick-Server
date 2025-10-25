from fastapi import FastAPI
from .routes import router
from .models import init_db
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    init_db()
    yield
    # shutdown (nothing)


app = FastAPI(title="Blind Stick Server", lifespan=lifespan)
app.include_router(router)