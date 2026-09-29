from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import db_incidents, store
from app.database.connection import get_db
from app.models_db import IncidentDB
from app.schemas import (
    IncidentListResponse,
    Tenant,
    TenantConfig,
    TenantListResponse,
)

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenant"])


def _tenant_exists(db: Session, tenant_id: str) -> bool:
    return (
        db.query(IncidentDB.tenant_id)
        .filter(IncidentDB.tenant_id == tenant_id)
        .first()
        is not None
    )


def _get_tenant(db: Session, tenant_id: str) -> Tenant:
    if not _tenant_exists(db, tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    return Tenant(tenant_id=tenant_id, name=db_incidents.humanize(tenant_id))


@router.get("", response_model=TenantListResponse)
def list_tenants(db: Session = Depends(get_db)):
    rows = (
        db.query(IncidentDB.tenant_id)
        .distinct()
        .order_by(IncidentDB.tenant_id.asc())
        .all()
    )
    items = [
        Tenant(
            tenant_id=row.tenant_id,
            name=(
                store.tenants[row.tenant_id].name
                if row.tenant_id in store.tenants
                else db_incidents.humanize(row.tenant_id)
            ),
        )
        for row in rows
    ]
    return TenantListResponse(items=items)


@router.get("/{tenant_id}/incidents", response_model=IncidentListResponse)
def list_tenant_incidents(
    tenant_id: str,
    platform_id: str | None = None,
    db: Session = Depends(get_db),
):
    _get_tenant(db, tenant_id)
    items = db_incidents.list_incidents(
        db, tenant_id=tenant_id, platform_id=platform_id
    )
    return IncidentListResponse(items=items)


@router.get("/{tenant_id}/config", response_model=TenantConfig)
def get_tenant_config(tenant_id: str, db: Session = Depends(get_db)):
    _get_tenant(db, tenant_id)
    config = store.tenant_configs.get(tenant_id)
    if config is None:
        config = TenantConfig(
            tenant_id=tenant_id,
            monitoring_enabled=True,
            remediation_policy="AUTO_LOW_RISK",
            allowed_actions=["Retry"],
        )
        store.tenant_configs[tenant_id] = config
    return config


@router.put("/{tenant_id}/config", response_model=TenantConfig)
def update_tenant_config(
    tenant_id: str, body: TenantConfig, db: Session = Depends(get_db)
):
    _get_tenant(db, tenant_id)
    body.tenant_id = tenant_id
    store.tenant_configs[tenant_id] = body
    return body
