"""Ecoclock Network - FastAPI server entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, me, tasks
from app.db.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)
	yield


app = FastAPI(
	title="Ecoclock Network API",
	description="Plataforma de confianza para donaciones verificadas y computo distribuido.",
	version="0.3.0",
	lifespan=lifespan,
)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

@app.get("/health")
def health_check():
	"""Comprueba que el servidor está vivo."""
	return {"status": "ok", "service": "ecoclock-network", "version": "0.3.0"}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(me.router, prefix="/me", tags=["me"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
