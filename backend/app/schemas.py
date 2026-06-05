from typing import Optional

from pydantic import BaseModel


class OrderRequest(BaseModel):
    pod_id: str
    symbol: str
    side: str                       # "buy" | "sell"
    qty: Optional[float] = None
    notional: Optional[float] = None
    order_type: str = "market"      # "market" | "limit"
    order_label: str = "market"     # what to record (market/limit/short/cover/...)
    limit_price: Optional[float] = None
    time_in_force: str = "day"


class CancelRequest(BaseModel):
    pod_id: str
    order_id: str


class CreatePodRequest(BaseModel):
    name: str
    asset_class: str
    benchmark_symbol: str = "SPY"
    description: Optional[str] = None
    allocated_capital: float = 0
    # Optionally attach Alpaca creds in the same call.
    alpaca_account_id: Optional[str] = None
    alpaca_api_key: Optional[str] = None
    alpaca_api_secret: Optional[str] = None


class SetAlpacaRequest(BaseModel):
    alpaca_account_id: Optional[str] = None
    alpaca_api_key: Optional[str] = None
    alpaca_api_secret: Optional[str] = None


class CapitalRequest(BaseModel):
    amount: float
    note: Optional[str] = None


class MembershipRequest(BaseModel):
    pod_id: str
    trader_id: str
    role: str = "trader"


class PortalLogin(BaseModel):
    credential: str


class TraderLogin(BaseModel):
    email: str
    password: str


class CreateTraderRequest(BaseModel):
    email: str
    password: str
    display_name: str
    is_admin: bool = False


class CreateTraderApiKeyRequest(BaseModel):
    name: str = "default"
