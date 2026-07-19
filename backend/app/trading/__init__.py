"""The /trading/* router — all trading-phase endpoints live here, behind the
auth seam (app/auth.py). Backtester today; watchlist scanner / paper / live
trading later, each added as a route on this same guarded router.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import backtest, service
from ..auth import require_trading_auth
from ..database import get_db
from ..providers import ProviderError
from ..schemas import BacktestRequest, BacktestResult

router = APIRouter(
    prefix="/trading",
    tags=["trading"],
    dependencies=[Depends(require_trading_auth)],
)


@router.get("/strategies")
def strategies():
    """List available backtest strategies for the UI picker."""
    return backtest.list_strategies()


@router.post("/backtest", response_model=BacktestResult)
def run_backtest(req: BacktestRequest, db: Session = Depends(get_db)):
    try:
        return service.run_backtest(db, req)
    except ValueError as e:
        # Bad strategy key / empty frame.
        raise HTTPException(status_code=400, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))
