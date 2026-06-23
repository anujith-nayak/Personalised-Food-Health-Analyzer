from fastapi import APIRouter

router = APIRouter(prefix="/scan", tags=["Food Scanner - Phase 2"])

_COMING_SOON = {"message": "Feature Coming in Phase 2", "status": "placeholder"}


@router.post("/packaged-food")
def scan_packaged_food():
    """Placeholder: OCR-based packaged food label scan (Phase 2)."""
    return _COMING_SOON


@router.post("/live-food")
def scan_live_food():
    """Placeholder: Live food image recognition (Phase 2)."""
    return _COMING_SOON
