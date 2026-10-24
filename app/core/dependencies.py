import secrets
from fastapi import Depends, Header, HTTPException
from app.core.config import settings
from app.core.security import verify_token
from app.services.users import get_user


def get_api_key(api_key: str = Header(...)):
    if not secrets.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(status_code=403, detail='Invalid API Key')
    

def get_current_user(token: str = Header(...)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail='Invalid JWT Token')
    # a valid token can outlive its account: a deleted user must lose access immediately (the admin lives in .env)
    account = payload.get('sub')
    if account != settings.ADMIN_USERNAME and not (account and get_user(account)):
        raise HTTPException(status_code=401, detail='Account no longer exists')
    return payload


def get_account(payload=Depends(get_current_user)) -> str:
    """The signed-in account: the user's email, or the admin name from .env."""
    return payload['sub']


def require_admin(account: str = Depends(get_account)) -> str:
    if account != settings.ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail='Admin only')
    return account
