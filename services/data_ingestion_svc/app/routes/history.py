"""Historical data versioning endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.data_ingestion_svc.app.models import (
    DataVersion,
    DataVersionCompare,
    HistoryQuery,
    DatasetSnapshotRequest,
)

router = APIRouter()


@router.post("/snapshots", response_model=DataVersion, status_code=201)
def create_snapshot(req: DatasetSnapshotRequest):
    """Create a point-in-time versioned snapshot of a dataset."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/versions/{dataset_id}", response_model=list[DataVersion])
def list_versions(dataset_id: str, limit: int = 50, offset: int = 0):
    """List all versions of a dataset ordered by version number descending."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/versions/{dataset_id}/{version_number}", response_model=DataVersion)
def get_version(dataset_id: str, version_number: int):
    """Retrieve metadata for a specific dataset version."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/versions/{dataset_id}/current", response_model=DataVersion)
def get_current_version(dataset_id: str):
    """Retrieve the current (latest active) version of a dataset."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/compare", response_model=DataVersionCompare)
def compare_versions(dataset_id: str, version_a: int, version_b: int):
    """Compare two versions of a dataset and return a diff summary."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/rollback/{dataset_id}/{version_number}", response_model=DataVersion)
def rollback_to_version(dataset_id: str, version_number: int):
    """Rollback a dataset to a previous version (creates a new version with old content)."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/versions/{dataset_id}/{version_number}", status_code=204)
def delete_version(dataset_id: str, version_number: int):
    """Delete a specific dataset version (cannot delete the current version)."""
    raise HTTPException(status_code=501, detail="Not implemented")
