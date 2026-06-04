from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    """
    Simple health verification endpoint.
    """
    return {"status": "ok"}
