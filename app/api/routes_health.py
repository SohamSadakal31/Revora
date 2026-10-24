from fastapi import APIRouter
from app.cache.redis_cache import redis_client
from app.services.model_service import DEALER_PREMIUM, MODEL_VERSION, model_meta

router = APIRouter()


@router.get('/health')
def health():
    try:
        redis_ok = bool(redis_client.ping())
    except Exception:
        redis_ok = False
    return {'status': 'ok', 'redis': 'ok' if redis_ok else 'unavailable',
            'model_version': MODEL_VERSION, 'model': model_meta, 'dealer_premium': DEALER_PREMIUM}
