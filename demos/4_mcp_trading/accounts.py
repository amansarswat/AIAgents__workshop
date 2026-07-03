"""
A tiny, self-contained trading-account model — NO external APIs.

The course version (6_mcp/accounts.py) pulls live prices from Polygon.io and
persists to SQLite. For a dependency-free demo we use a fixed price
table and a single local JSON file. The interface is the same, so the MCP server
on top of it is unchanged in spirit.
"""

import json
from pathlib import Path
from datetime import datetime

INITIAL_BALANCE = 10_000.0
STORE = Path(__file__).resolve().parent / "accounts.json"

# Orbit's product catalog (SKU -> unit price). In production this comes from the catalog service.
PRICES = {
    "WIDGET": 49.0, "GADGET": 120.0, "GIZMO": 999.0,
    "DOODAD": 19.0, "SPROCKET": 8.0, "BUNDLE": 250.0,
}


def get_share_price(symbol: str) -> float:
    return PRICES.get(symbol.upper(), 0.0)


def _load_all() -> dict:
    if STORE.exists():
        return json.loads(STORE.read_text(encoding="utf-8"))
    return {}


def _save_all(data: dict) -> None:
    STORE.write_text(json.dumps(data, indent=2), encoding="utf-8")


class Account:
    def __init__(self, name: str, balance: float, holdings: dict, transactions: list):
        self.name = name
        self.balance = balance
        self.holdings = holdings
        self.transactions = transactions

    @classmethod
    def get(cls, name: str) -> "Account":
        name = name.lower()
        data = _load_all()
        if name not in data:
            data[name] = {"balance": INITIAL_BALANCE, "holdings": {}, "transactions": []}
            _save_all(data)
        a = data[name]
        return cls(name, a["balance"], a["holdings"], a["transactions"])

    def save(self) -> None:
        data = _load_all()
        data[self.name] = {
            "balance": self.balance,
            "holdings": self.holdings,
            "transactions": self.transactions,
        }
        _save_all(data)

    def buy_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        symbol = symbol.upper()
        price = get_share_price(symbol)
        if price == 0:
            raise ValueError(f"Unknown symbol {symbol}")
        cost = price * quantity
        if cost > self.balance:
            raise ValueError("Insufficient funds.")
        self.balance -= cost
        self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
        self.transactions.append(
            {"symbol": symbol, "quantity": quantity, "price": price,
             "timestamp": datetime.now().isoformat(timespec="seconds"), "rationale": rationale}
        )
        self.save()
        return self.report()

    def sell_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        symbol = symbol.upper()
        if self.holdings.get(symbol, 0) < quantity:
            raise ValueError(f"Not enough {symbol} shares to sell.")
        price = get_share_price(symbol)
        self.balance += price * quantity
        self.holdings[symbol] -= quantity
        if self.holdings[symbol] == 0:
            del self.holdings[symbol]
        self.transactions.append(
            {"symbol": symbol, "quantity": -quantity, "price": price,
             "timestamp": datetime.now().isoformat(timespec="seconds"), "rationale": rationale}
        )
        self.save()
        return self.report()

    def portfolio_value(self) -> float:
        value = self.balance
        for symbol, qty in self.holdings.items():
            value += get_share_price(symbol) * qty
        return round(value, 2)

    def report(self) -> str:
        return json.dumps({
            "name": self.name,
            "store_credit": round(self.balance, 2),
            "items": self.holdings,
            "account_value": self.portfolio_value(),
        })
