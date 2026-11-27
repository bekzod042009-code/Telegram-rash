import asyncio
import contextlib
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import bot, config, db
from .routes import admin, common, student, teacher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
WEB = Path(__file__).resolve().parent.parent / "web"


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    task = asyncio.create_task(bot.run())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await db.close()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(RequestValidationError)
async def bad_request(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": "Maʼlumot notoʻgʻri kiritilgan."}, status_code=422)


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers.setdefault("Cache-Control", "no-cache")
    return response


@app.get("/health")
async def health():
    await db.pool.fetchval("SELECT 1")
    return {"ok": True}


for module in (common, teacher, student, admin):
    app.include_router(module.router)
app.mount("/", StaticFiles(directory=WEB, html=True), name="web")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
