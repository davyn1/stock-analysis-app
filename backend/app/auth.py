"""Auth gate for /trading/* routes.

Deployment-ready seam, not a full auth system. It is OPEN when no token is
configured (local/dev — backtesting is read-only math on historical data, no
reason to lock yourself out) and ENFORCED the moment TRADING_TOKEN is set (e.g.
on deploy, or when a state-changing feature like paper/live trading lands).

Every /trading route depends on this, so tightening it later — swap the shared
token for real per-user auth when live trading (broker keys server-side) lands —
is a change to this one function, not to any route signature.
"""
from fastapi import Header, HTTPException, status

from .config import settings


def require_trading_auth(authorization: str | None = Header(default=None)) -> None:
    expected = settings.trading_token.strip()
    if not expected:
        return  # unconfigured -> open (local/dev)
    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid trading token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
