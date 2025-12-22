"""
Idempotency decorator to prevent duplicate requests.
"""

from functools import wraps
from fastapi import Request, HTTPException
from app.core.database import db

def idempotent_request(func):
    """
    Decorator to ensure a request is processed only once.

    Checks for an 'Idempotency-Key' header and uses it to prevent
    re-processing of the same request.

    Raises:
        HTTPException(400): If 'Idempotency-Key' header is missing.
        HTTPException(409): If the key has already been processed.
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        idempotency_key = request.headers.get("Idempotency-Key")

        if not idempotency_key:
            raise HTTPException(
                status_code=400, detail="Idempotency-Key header is required"
            )

        if db.is_key_used(idempotency_key):
            raise HTTPException(
                status_code=409,
                detail="This request has already been processed.",
            )

        # Mark key as used BEFORE processing the request
        db.mark_key_as_used(idempotency_key)

        # Proceed with the actual function
        return await func(request, *args, **kwargs)

    return wrapper
