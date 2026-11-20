"""Ecoclock Network - FastAPI server entry point."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin, auth, expeditions, impact, me, nodes, tasks
from app.db.database import Base, engine


ADMIN_HTML = Path(__file__).parent / "static" / "admin.html"

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


# Crear carpeta si no existe
Path("uploads").mkdir(exist_ok=True)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(me.router, prefix="/me", tags=["me"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(expeditions.router, prefix="/expeditions", tags=["expeditions"])
app.include_router(nodes.router, prefix="/nodes", tags=["nodes"])
app.include_router(impact.router)
app.include_router(admin.router)

# Estáticos y panel admin
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/admin", include_in_schema=False)
async def admin_page():
    return FileResponse(ADMIN_HTML, media_type="text/html")