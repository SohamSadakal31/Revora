import base64
import binascii
import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.dependencies import get_account, get_api_key, get_current_user
from app.services import mailer
from app.services.model_service import predict_car_price, UnknownValueError, KNOWN_VALUES
from app.services.usage_log import log_search, usage_stats, user_history
from app.services.users import EMAIL_RULE, email_allowed

router = APIRouter()


class CarFeatures(BaseModel):
    company: str = Field(examples=['Maruti'])
    model: str = Field(examples=['Swift'])
    edition: str = Field('', description='Variant / trim, e.g. "VXI" - optional, but improves accuracy',
                         examples=['VDI'])
    year: int = Field(ge=1980, le=date.today().year, examples=[2015])
    owner: str = Field(examples=['First'])
    fuel: str = Field(examples=['Diesel'])
    seller_type: str = Field(examples=['Individual'])
    transmission: str = Field(examples=['Manual'])
    km_driven: float = Field(ge=0, le=1_000_000, examples=[60000])
    mileage_mpg: float | None = Field(None, gt=0, le=150, examples=[55],
                                      description='Fuel economy (km/l x 2.352). Leave empty if unknown or for CNG/LPG')
    engine_cc: float = Field(ge=500, le=7000, examples=[1248])
    max_power_bhp: float = Field(ge=20, le=700, examples=[74])
    torque_nm: float = Field(ge=30, le=2000, examples=[190])
    seats: float = Field(ge=2, le=14, examples=[5])


class ShareQuotation(BaseModel):
    to: str = Field(max_length=254, examples=['customer@example.com'])
    filename: str = Field(max_length=80, pattern=r'^[A-Za-z0-9._-]+\.pdf$', examples=['QT-20260930-ABC123.pdf'])
    pdf_base64: str = Field(max_length=7_000_000)
    message: str = Field('', max_length=1000)


@router.post('/predict')
def predict_price(car: CarFeatures, account: str = Depends(get_account), _=Depends(get_api_key)):
    try:
        result = predict_car_price(car.model_dump())
    except UnknownValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    log_search(car.model_dump(), result, account)
    return {'predicted_price': f"{result['price']:,.2f}", **result}


@router.get('/options')
def options():
    """Accepted values for the text fields (case-insensitive)."""
    return {col: sorted(values) for col, values in KNOWN_VALUES.items()}


@router.get('/stats')
def stats(user=Depends(get_current_user), _=Depends(get_api_key)):
    """Most searched cars - what clients are looking for."""
    return usage_stats()


@router.get('/history')
def history(account: str = Depends(get_account), _=Depends(get_api_key)):
    """The signed-in user's own estimates, newest first (last 50)."""
    return user_history(account)


@router.post('/share/quotation', status_code=202)
def share_quotation(data: ShareQuotation, account: str = Depends(get_account), _=Depends(get_api_key)):
    """Email a quotation PDF (made by the website) to a customer."""
    if not mailer.is_configured():
        raise HTTPException(status_code=503, detail='Sending quotations by email is not available yet.')
    to = data.to.strip()
    if not EMAIL_RULE.match(to):
        raise HTTPException(status_code=422, detail='Enter a valid email address.')
    try:
        pdf = base64.b64decode(data.pdf_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail='The quotation file is not valid.')
    if not pdf.startswith(b'%PDF'):
        raise HTTPException(status_code=422, detail='The quotation file is not a PDF.')
    if not email_allowed(account):
        raise HTTPException(status_code=429, detail='Daily email limit reached. Please try again tomorrow.')
    note = data.message.strip()
    body = (f'{note}\n\n' if note else '') + (
        f'Please find attached your used-car price quotation from {settings.APP_NAME}.\n\n'
        'This quotation is an indicative market valuation, not an offer to buy or sell.')
    try:
        mailer.send_email(to, f'Your used-car price quotation - {settings.APP_NAME}', body,
                          [(data.filename, pdf, 'application/pdf')])
    except Exception:
        logging.exception('Could not send the quotation email')
        raise HTTPException(status_code=503, detail='The email could not be sent. Please try again later.')
    return {'detail': f'Quotation sent to {to}.'}
