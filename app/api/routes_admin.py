from fastapi import APIRouter, Depends
from app.core.dependencies import get_api_key, require_admin
from app.services.usage_log import admin_usage, usage_stats
from app.services.users import count_users, signups_per_day

router = APIRouter()


@router.get('/admin/stats')
def admin_stats(_admin: str = Depends(require_admin), _key=Depends(get_api_key)):
    """Business overview for the admin account only: users, sign-ups and estimates."""
    usage = usage_stats(top=10)
    return {
        'registered_users': count_users(),
        'signups_per_day': [{'day': d, 'signups': n} for d, n in signups_per_day(30)],
        'total_estimates': usage['total_searches'],
        'most_searched': usage['most_searched'],
        **admin_usage(30),
    }
