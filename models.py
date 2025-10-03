from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, PrivateAttr
import uuid


class ReportHeader(BaseModel):
    reporter_name: str = Field(default="")
    report_date: date = Field(default_factory=date.today)
    trip_purpose: str = Field(default="")
    client: str = Field(default="")
    visit_type: str = Field(default="")
    base_currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    fx_usd_to_mxn: float = Field(default=18.0, ge=0.0001, description="User-provided FX: 1 USD = X MXN")


class ExpenseEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    merchant_name: Optional[str] = None
    transaction_date: Optional[date] = None
    transaction_time: Optional[str] = None  # HH:MM or free text
    total_amount: Optional[float] = None
    currency_code: str = Field(default="USD")
    payment_method: Optional[str] = None
    category: Optional[str] = None
    notes: str = Field(default="")
    source_name: Optional[str] = None  # original file name

    # Non-serialized helpers (private attribute)
    _image_bytes: Optional[bytes] = PrivateAttr(default=None)

    def to_row(self) -> Dict[str, Any]:
        return {
            "ID": self.id,
            "Merchant": self.merchant_name or "",
            "Date": self.transaction_date.isoformat() if self.transaction_date else "",
            "Time": self.transaction_time or "",
            "Total": self.total_amount if self.total_amount is not None else "",
            "Currency": self.currency_code,
            "Payment Method": self.payment_method or "",
            "Category": self.category or "",
            "Notes": self.notes,
            "Source": self.source_name or "",
        }


DEFAULT_CATEGORIES: List[str] = [
    "Food & Meals",
    "Gas Station",
    "Toll",
    "Lodging",
    "Transportation",
    "Parking",
    "Other",
]

DEFAULT_PAYMENT_METHODS: List[str] = [
    "Cash",
    "Credit Card",
    "Debit Card",
    "Digital Wallet",
    "Bank Transfer",
    "Other",
]

