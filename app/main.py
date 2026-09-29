from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from app.database.connection import SessionLocal, engine
from app.routers import incidents, tenants, platforms
from app.seed import init_db, seed_if_empty

app = FastAPI(title="Autonomous Pipeline Incident API")
app.include_router(incidents.router)
app.include_router(tenants.router)
app.include_router(platforms.router)


@app.on_event("startup")
def on_startup():
    init_db(engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
