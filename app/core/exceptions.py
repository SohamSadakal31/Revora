import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # full details go to the server log, never to the client
        logging.exception(f'Unhandled error on {request.method} {request.url.path}')
        return JSONResponse(status_code=500, content={'detail': 'Internal server error'})
