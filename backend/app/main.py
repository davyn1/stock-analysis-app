"""FastAPI entrypoint."""
# Use the OS trust store for TLS. This is a no-op on a normal machine, but on a
# corporate laptop behind a TLS-inspecting proxy it lets httpx-based clients
# (Twelve Data, Finnhub, the Anthropic SDK) trust the proxy's root CA without
# manual cert config. Must run before any TLS connections are made.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import get_db, init_db
from .providers import ProviderError
from .schemas import AnalyzeRequest, AnalyzeResponse
from . import service

app = FastAPI(title="Personalized Stock Analysis", version="0.1.0")

# Two-user personal app — allow the local dev frontend. Tighten for deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, db: Session = Depends(get_db)):
    try:
        return service.analyze(db, req)
    except ProviderError as e:
        # Data-source problems (bad ticker, free-tier limits, auth) -> 502.
        raise HTTPException(status_code=502, detail=str(e))
