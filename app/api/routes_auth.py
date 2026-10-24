import logging
import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from app.core.config import settings
from app.core.dependencies import get_account, get_current_user
from app.core.security import create_token
from app.services import mailer
from app.services.usage_log import delete_user_history
from app.services.users import (
    UserError, UserExistsError, authenticate, change_password, clear_failed_logins, create_reset_code, create_user,
    delete_user, discard_reset_codes, get_user, minutes_locked, record_failed_login, reset_password,
)

router = APIRouter()
RESET_SENT = 'If an account exists for this email, a reset code has been sent to it.'


class AuthInput(BaseModel):
    email: str | None = Field(None, examples=['rahul@example.com'])
    username: str | None = Field(None, description='Only for the admin account configured in .env')
    password: str

    @model_validator(mode='after')
    def one_login_name(self):
        if not (self.email or self.username):
            raise ValueError('email is required')
        return self


class RegisterInput(BaseModel):
    email: str = Field(max_length=254, examples=['rahul@example.com'])
    password: str = Field(examples=['Str0ngPassw0rd'])
    full_name: str = Field('', max_length=60, examples=['Rahul Sharma'])


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordConfirm(BaseModel):
    password: str


class ForgotInput(BaseModel):
    email: str = Field(max_length=254)


class ResetInput(BaseModel):
    email: str = Field(max_length=254)
    code: str = Field(max_length=12)
    new_password: str


def _token_response(account: str, full_name: str = '', is_admin: bool = False) -> dict:
    token = create_token({'sub': account}, expire_minutes=settings.JWT_EXPIRE_MINUTES)
    return {'access_token': token, 'email': account, 'full_name': full_name, 'is_admin': is_admin}


def _is_admin(login: str, password: str) -> bool:
    # compare_digest takes the same time for right and wrong guesses, so timing leaks nothing
    valid_user = secrets.compare_digest(login, settings.ADMIN_USERNAME)
    valid_password = secrets.compare_digest(password, settings.ADMIN_PASSWORD)
    return valid_user and valid_password


def _user_only(account: str) -> str:
    if account == settings.ADMIN_USERNAME:
        raise HTTPException(status_code=400, detail='The admin account is managed in the .env file.')
    return account


@router.post('/register', status_code=201)
def register(data: RegisterInput):
    try:
        user = create_user(data.email, data.password, data.full_name)
    except UserExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except UserError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _token_response(user['email'], user['full_name'])


@router.post('/login')
def login(auth: AuthInput):
    login_name = auth.email or auth.username
    locked = minutes_locked(login_name)
    if locked:
        raise HTTPException(status_code=429, detail=f'Too many failed attempts. Try again in {locked} minute(s) '
                                                    'or reset your password.')
    if _is_admin(login_name, auth.password):
        clear_failed_logins(login_name)
        return _token_response(login_name, 'Administrator', is_admin=True)
    user = authenticate(login_name, auth.password)
    if user is None:
        record_failed_login(login_name)
        raise HTTPException(status_code=401, detail='Invalid credentials')
    clear_failed_logins(login_name)
    return _token_response(user['email'], user['full_name'])


@router.get('/me')
def me(payload=Depends(get_current_user)):
    account = payload['sub']
    if account == settings.ADMIN_USERNAME:
        return {'email': None, 'full_name': 'Administrator', 'is_admin': True}
    user = get_user(account)
    if user is None:
        raise HTTPException(status_code=401, detail='Account no longer exists')
    return dict(user, is_admin=False)


@router.post('/account/password')
def change_my_password(data: PasswordChange, account: str = Depends(get_account)):
    try:
        change_password(_user_only(account), data.current_password, data.new_password)
    except UserError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {'detail': 'Password changed.'}


@router.post('/account/delete')
def delete_my_account(data: PasswordConfirm, account: str = Depends(get_account)):
    """Deletes the account and every estimate it made (right to erasure, DPDP Act 2023)."""
    try:
        delete_user(_user_only(account), data.password)
    except UserError as e:
        raise HTTPException(status_code=422, detail=str(e))
    removed = delete_user_history(account)
    return {'detail': 'Your account and your data have been deleted.', 'estimates_deleted': removed}


@router.post('/password/forgot', status_code=202)
def forgot_password(data: ForgotInput):
    if not mailer.is_configured():
        raise HTTPException(status_code=503, detail='Password reset by email is not available yet.')
    code = create_reset_code(data.email)
    if code:  # same answer whether or not the account exists, so emails can't be probed
        try:
            mailer.send_email(data.email.strip(), f'{settings.APP_NAME} - password reset code',
                              f'Your password reset code is {code}.\n\nIt expires in {settings.RESET_CODE_MINUTES} '
                              'minutes. If you did not ask to reset your password, you can ignore this email.')
        except Exception:
            logging.exception('Could not send the password reset email')
            discard_reset_codes(data.email)
            raise HTTPException(status_code=503, detail='The email could not be sent. Please try again later.')
    return {'detail': RESET_SENT}


@router.post('/password/reset')
def reset_my_password(data: ResetInput):
    try:
        reset_password(data.email, data.code, data.new_password)
    except UserError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {'detail': 'Password reset. You can now log in with your new password.'}
