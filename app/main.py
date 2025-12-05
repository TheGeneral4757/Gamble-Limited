import sys
from pathlib import Path

# Add parent directory to path so imports work when running directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.routers import pages, api, admin
from app.routers.auth import router as auth_router
from app.config import settings

app = FastAPI(title=settings.server.name)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth_router)  # Auth routes first
app.include_router(pages.router)
app.include_router(api.router, prefix="/api")
app.include_router(admin.router, prefix="/admin")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=True
    )
