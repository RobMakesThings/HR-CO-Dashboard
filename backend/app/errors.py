from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ClientError(Exception):
    def __init__(self, status_code: int, code: str, detail: str):
        self.status_code = status_code
        self.code = code
        self.detail = detail
        super().__init__(detail)


def _env(status_code: int, code: str, detail: str) -> dict:
    return {"detail": detail, "code": code}


def init_handlers(app):
    @app.exception_handler(ClientError)
    async def client_error_handler(_req: Request, exc: ClientError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_env(exc.status_code, exc.code, exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_req: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422, content=_env(422, "VALIDATION", str(exc.errors()))
        )
