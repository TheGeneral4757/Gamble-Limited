import sys
import os

# Add project root to sys.path to allow running as script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.routers import pages, api, admin

app = FastAPI(
    title=settings.server.name,
    debug=settings.server.debug
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(pages.router)
app.include_router(api.router, prefix="/api")
app.include_router(admin.router, prefix="/admin")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.debug
    )
