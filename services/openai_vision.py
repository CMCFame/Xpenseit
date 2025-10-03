from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any, Dict, Optional

from openai import OpenAI


SYSTEM_PROMPT = (
    "You are an elite receipt parser. Extract key fields with high precision. "
    "If a field is missing or unclear, set it to null. Dates should be ISO (YYYY-MM-DD). "
    "Time should be 24h HH:MM if present. Currency is a 3-letter code like USD or MXN. "
    "Payment method: Cash, Credit Card, Debit Card, Digital Wallet, Bank Transfer, Other. "
    "Category should be one of: Food & Meals, Gas Station, Toll, Lodging, Transportation, Parking, Other. "
    "Return STRICT JSON only, with these keys: merchant_name, transaction_date, transaction_time, total_amount, currency_code, payment_method, category."
)


def _b64_image(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def extract_expense_fields(image_bytes: bytes, file_name: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Calls OpenAI Vision to extract expense fields from an image.
    Returns a dict with canonical keys suitable for ExpenseEntry.
    """
    client = OpenAI()

    img_b64 = _b64_image(image_bytes)
    user_content = [
        {"type": "text", "text": SYSTEM_PROMPT},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
        },
    ]

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": user_content}],
            temperature=0.1,
        )
        text = completion.choices[0].message.content or "{}"
        # Try to parse JSON from the response. Model should return pure JSON.
        data = None
        try:
            data = json.loads(text)
        except Exception:
            # Attempt to extract JSON substring if extra text leaked
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = json.loads(text[start : end + 1])
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    # Normalize fields
    result: Dict[str, Any] = {
        "merchant_name": _norm_str(data.get("merchant_name")),
        "transaction_date": _norm_date(data.get("transaction_date")),
        "transaction_time": _norm_time(data.get("transaction_time")),
        "total_amount": _norm_float(data.get("total_amount")),
        "currency_code": _norm_currency(data.get("currency_code")),
        "payment_method": _norm_str(data.get("payment_method")),
        "category": _norm_str(data.get("category")),
        "source_name": file_name,
    }
    return result


def _norm_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _norm_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        s = str(value).replace(",", "")
        return float(s)
    except Exception:
        return None


def _norm_currency(value: Any) -> str:
    if not value:
        return "USD"
    s = str(value).upper().strip()
    if len(s) == 1:  # symbols
        return {"$": "USD"}.get(s, "USD")
    return s


def _norm_date(value: Any):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
        return dt.date()
    except Exception:
        # Try common formats
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(str(value), fmt).date()
            except Exception:
                continue
        return None


def _norm_time(value: Any) -> Optional[str]:
    if not value:
        return None
    s = str(value).strip()
    # Basic sanity: HH:MM variants
    parts = s.split(":")
    if len(parts) >= 2 and all(p.isdigit() for p in parts[:2]):
        hh = int(parts[0]) % 24
        mm = int(parts[1]) % 60
        return f"{hh:02d}:{mm:02d}"
    return None


