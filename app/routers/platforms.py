from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import store
from app.database.connection import get_db
from app.models_db import IncidentDB
from app.schemas import Platform, PlatformConfig, PlatformListResponse

router = APIRouter(prefix="/api/v1/platforms", tags=["Platform"])


def _platform_exists(db: Session, platform_id: str) -> bool:
    return (
        db.query(IncidentDB.platform_id)
        .filter(IncidentDB.platform_id == platform_id)
        .first()
        is not None
    )


@router.get("", response_model=PlatformListResponse)
def list_platforms(db: Session = Depends(get_db)):
    rows = (
        db.query(IncidentDB.platform_id)
        .distinct()
        .order_by(IncidentDB.platform_id.asc())
        .all()
    )
    items = [
        Platform(
            platform_id=row.platform_id,
            name=(
                store.platforms[row.platform_id].name
                if row.platform_id in store.platforms
                else row.platform_id
            ),
        )
        for row in rows
    ]
    return PlatformListResponse(items=items)


@router.get("/{platform}/config", response_model=PlatformConfig)
def get_platform_config(platform: str, db: Session = Depends(get_db)):
    if not _platform_exists(db, platform):
        raise HTTPException(status_code=404, detail="Platform not found")
    config = store.platform_configs.get(platform)
    if config is None:
        config = PlatformConfig(platform_id=platform, config={})
        store.platform_configs[platform] = config
    return config
