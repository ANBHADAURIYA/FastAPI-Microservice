from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Documented in OpenAPI so clients know the shape of every failure."""

    error: ErrorDetail
    request_id: str
