"""Pricing vendor integration endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.data_ingestion_svc.app.models import (
    VendorConfig,
    VendorConfigOut,
    VendorSyncRequest,
    VendorSyncStatus,
)

router = APIRouter()


@router.post("/", response_model=VendorConfigOut, status_code=201)
def create_vendor_config(req: VendorConfig):
    """Register a new pricing/data vendor configuration."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/", response_model=list[VendorConfigOut])
def list_vendor_configs(vendor_type: str | None = None, enabled: bool | None = None):
    """List all registered vendor configurations with optional filters."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{vendor_id}", response_model=VendorConfigOut)
def get_vendor_config(vendor_id: str):
    """Retrieve a vendor configuration by ID."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put("/{vendor_id}", response_model=VendorConfigOut)
def update_vendor_config(vendor_id: str, req: VendorConfig):
    """Update an existing vendor configuration."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{vendor_id}", status_code=204)
def delete_vendor_config(vendor_id: str):
    """Remove a vendor configuration."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/sync", response_model=VendorSyncStatus, status_code=201)
def trigger_vendor_sync(req: VendorSyncRequest):
    """Trigger a data synchronisation job for a vendor (full or incremental)."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/sync/{sync_id}", response_model=VendorSyncStatus)
def get_sync_status(sync_id: str):
    """Check the status of a vendor sync job."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{vendor_id}/sync-history", response_model=list[VendorSyncStatus])
def get_vendor_sync_history(vendor_id: str, limit: int = 20):
    """Retrieve the sync history for a vendor."""
    raise HTTPException(status_code=501, detail="Not implemented")
