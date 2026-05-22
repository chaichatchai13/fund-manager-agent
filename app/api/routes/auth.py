from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.auth.security import COOKIE_NAME, cookie_kwargs, create_token, verify_password
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    if not settings.thetaflow_password:
        raise HTTPException(
            status_code=500,
            detail="THETAFLOW_PASSWORD is not set — configure it in your .env file",
        )

    if not verify_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_token()
    response.set_cookie(value=token, **cookie_kwargs())
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, httponly=True, samesite="lax")
    return {"ok": True}


@router.get("/me")
async def me(request: Request):
    """Returns 200 if the caller has a valid session, 401 otherwise."""
    from app.auth.security import COOKIE_NAME, decode_token
    token = request.cookies.get(COOKIE_NAME)
    if not token or not decode_token(token):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"authenticated": True}
