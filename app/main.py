import logging
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.api import routes_admin, routes_auth, routes_predict, routes_health
from app.middleware.logging_middleware import LoggingMiddleware
from app.core.exceptions import register_exception_handlers

logging.basicConfig(level=logging.INFO)

app = FastAPI(title='Car Price Prediction API')

# link middleware
app.add_middleware(LoggingMiddleware)

# link endpoints
app.include_router(routes_auth.router, tags=['Auth'])
app.include_router(routes_predict.router, tags=['Prediction'])
app.include_router(routes_health.router, tags=['Health'])
app.include_router(routes_admin.router, tags=['Admin'])

# monitoring using Prometheus
Instrumentator().instrument(app).expose(app)

# add exception handler
register_exception_handlers(app)
