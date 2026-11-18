"""FastAPI application entry point: CORS, routing and domain-error translation."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.services import BusinessRuleError

logger = logging.getLogger("eduflow")

app = FastAPI(title="EduFlow API", version="1.0.0")

# The SPA is served from Vite during development; restrict origins explicitly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.exception_handler(BusinessRuleError)
async def business_rule_handler(request: Request, exc: BusinessRuleError) -> JSONResponse:
    # Business denials and validation failures are security-relevant; log context only.
    logger.warning("business_rule=%s status=%s path=%s", exc.message, exc.status_code, request.url.path)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}
