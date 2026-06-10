from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.canva_oauth import CanvaOAuthState
from src.schemas.canva_oauth import CanvaOAuthCallbackRead, CanvaOAuthRefreshRead, CanvaOAuthStatusRead
from src.services.canva_oauth_service import CanvaOAuthService


router = APIRouter()


@router.get("/canva/oauth/status", response_model=CanvaOAuthStatusRead)
def get_canva_oauth_status(db: Session = Depends(get_db)):
    service = CanvaOAuthService(db)
    return service.get_status()


@router.get("/canva/oauth/start")
def start_canva_oauth(
    redirect_after: str | None = Query(None),
    json: bool = Query(False),
    db: Session = Depends(get_db),
):
    service = CanvaOAuthService(db)
    try:
        authorization_url = service.start_authorization(redirect_after=redirect_after)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if json:
        return JSONResponse({"authorization_url": authorization_url})
    return RedirectResponse(authorization_url, status_code=307)


@router.get("/canva/oauth/callback", response_model=CanvaOAuthCallbackRead)
def canva_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    json: bool = Query(False),
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"Erro OAuth do Canva: {error_description or error}",
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Callback OAuth do Canva sem code. Verifique redirect_uri, scopes e autorização no Canva Developer Portal.",
        )

    if not state:
        raise HTTPException(status_code=400, detail="Callback OAuth do Canva sem state.")

    service = CanvaOAuthService(db)
    try:
        token = service.handle_callback(code=code, state=state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        detail = str(exc)
        if detail.startswith("Canva não configurado"):
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)

    oauth_state = (
        db.query(CanvaOAuthState)
        .filter(CanvaOAuthState.state == state)
        .first()
    )
    if oauth_state and oauth_state.redirect_after:
        return RedirectResponse(oauth_state.redirect_after, status_code=303)

    if json:
        return CanvaOAuthCallbackRead(
            connected=True,
            message="Canva conectado com sucesso.",
            expires_at=token.expires_at,
        )

    html = """
    <html>
      <head><title>Canva conectado</title></head>
      <body style="font-family: sans-serif; padding: 2rem;">
        <h1>Canva conectado com sucesso.</h1>
        <p>Pode fechar esta aba.</p>
      </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)


@router.post("/canva/oauth/refresh", response_model=CanvaOAuthRefreshRead)
def refresh_canva_oauth_token(db: Session = Depends(get_db)):
    service = CanvaOAuthService(db)
    try:
        token = service.refresh_access_token()
    except RuntimeError as exc:
        detail = str(exc)
        if detail.startswith("Canva não configurado") or detail.startswith("Canva não conectado"):
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)

    return CanvaOAuthRefreshRead(
        refreshed=True,
        expires_at=token.expires_at,
        message="Token OAuth do Canva renovado com sucesso.",
    )
