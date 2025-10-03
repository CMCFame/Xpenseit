from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
import requests


EXCHANGE_API = "https://api.exchangerate.host/latest"


def fetch_rates(base: str = "USD") -> Dict[str, float]:
    try:
        resp = requests.get(EXCHANGE_API, params={"base": base}, timeout=10)
        data = resp.json()
        rates = data.get("rates", {})
        # Ensure base currency rate 1.0
        rates[base] = 1.0
        return rates
    except Exception:
        # Fallback simple mapping if offline
        if base == "USD":
            return {"USD": 1.0, "MXN": 18.0}
        if base == "MXN":
            return {"USD": 1.0 / 18.0, "MXN": 1.0}
        return {base: 1.0}


def convert(amount: float, from_ccy: str, to_ccy: str, rates: Dict[str, float]) -> float:
    from_ccy = from_ccy.upper()
    to_ccy = to_ccy.upper()
    if from_ccy not in rates or to_ccy not in rates:
        return amount
    if from_ccy == to_ccy:
        return amount
    # Convert via base rates map
    base_amount = amount / rates[from_ccy]
    return base_amount * rates[to_ccy]


