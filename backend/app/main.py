import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.gas_fields import router as gas_fields_router
from app.api.pipelines import router as pipelines_router
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(title="Tepuy Gas Intelligence API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


app.include_router(pipelines_router)
app.include_router(gas_fields_router)
