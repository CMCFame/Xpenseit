from __future__ import annotations

import io
from typing import List, Dict, Any
import pandas as pd
import streamlit as st
from PIL import Image

from xpenseit.models import ExpenseEntry, ReportHeader, DEFAULT_CATEGORIES, DEFAULT_PAYMENT_METHODS
from pandas import ExcelWriter
import datetime as _dt


def render_header_form(state_key: str = "header") -> ReportHeader:
    st.subheader("Report Header")
    cols = st.columns(3)
    with cols[0]:
        reporter_name = st.text_input("Reporter Name", key=f"{state_key}_name")
        client = st.text_input("Client", key=f"{state_key}_client")
    with cols[1]:
        report_date = st.date_input("Report Date", key=f"{state_key}_date")
        visit_type = st.text_input("Visit Type", key=f"{state_key}_visit")
    with cols[2]:
        trip_purpose = st.text_input("Trip Purpose", key=f"{state_key}_purpose")
        base_currency = st.selectbox("Base Currency", options=["USD", "MXN"], key=f"{state_key}_ccy")
    fx_usd_to_mxn = st.number_input("1 USD equals (MXN)", min_value=0.0001, value=18.0, step=0.01, key=f"{state_key}_fx")

    return ReportHeader(
        reporter_name=reporter_name,
        report_date=report_date,
        trip_purpose=trip_purpose,
        client=client,
        visit_type=visit_type,
        base_currency=base_currency,
        fx_usd_to_mxn=fx_usd_to_mxn,
    )


def render_expenses_table(entries: List[ExpenseEntry]) -> pd.DataFrame:
    st.subheader("Expenses")
    df = pd.DataFrame([e.to_row() for e in entries])
    if df.empty:
        st.info("No expenses yet. Upload images or PDFs to get started.")
        return df

    edited = st.data_editor(
        df,
        key="expenses_editor",
        width='stretch',
        column_config={
            "Notes": st.column_config.TextColumn(width="medium"),
            "Category": st.column_config.SelectboxColumn(options=DEFAULT_CATEGORIES),
            "Payment Method": st.column_config.SelectboxColumn(options=DEFAULT_PAYMENT_METHODS),
            "Currency": st.column_config.SelectboxColumn(options=["USD", "MXN"]),
            "Total": st.column_config.NumberColumn(format="%.2f"),
        },
        hide_index=True,
    )
    return edited


def render_image_gallery(entries: List[ExpenseEntry]):
    if not entries:
        return
    st.subheader("Receipts Preview")
    cols = st.columns(3)
    for i, entry in enumerate(entries):
        if entry._image_bytes:
            with cols[i % 3]:
                st.caption(entry.source_name or "Receipt")
                st.image(entry._image_bytes, width='stretch')


def get_download_bytes(df: pd.DataFrame, header: ReportHeader) -> Dict[str, bytes]:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    json_bytes = df.to_json(orient="records", indent=2).encode("utf-8")
    # Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Summary sheet with totals similar to PDF
        summary_rows = [
            ["Reporter", header.reporter_name],
            ["Date", header.report_date.isoformat()],
            ["Trip Purpose", header.trip_purpose],
            ["Client", header.client],
            ["Visit Type", header.visit_type],
            ["Base Currency", header.base_currency],
            ["FX (1 USD)", f"{header.fx_usd_to_mxn:.4f} MXN"],
        ]
        summary = pd.DataFrame(summary_rows, columns=["Field", "Value"])
        summary.to_excel(writer, index=False, sheet_name="Summary")

        # Expenses sheet
        df.to_excel(writer, index=False, sheet_name="Expenses")

        # Totals sheet
        usd_sub = df.loc[df["Currency"].str.upper() == "USD", "Total"].fillna(0).astype(float).sum() if not df.empty else 0.0
        mxn_sub = df.loc[df["Currency"].str.upper() == "MXN", "Total"].fillna(0).astype(float).sum() if not df.empty else 0.0
        total_usd = usd_sub + (mxn_sub / (header.fx_usd_to_mxn or 1))
        total_mxn = mxn_sub + (usd_sub * (header.fx_usd_to_mxn or 1))
        totals = pd.DataFrame([
            ["Subtotal USD", f"{usd_sub:,.2f} USD"],
            ["Subtotal MXN", f"{mxn_sub:,.2f} MXN"],
            ["Total USD", f"{total_usd:,.2f} USD"],
            ["Total MXN", f"{total_mxn:,.2f} MXN"],
        ], columns=["Metric", "Value"])
        totals.to_excel(writer, index=False, sheet_name="Totals")
    xlsx_bytes = output.getvalue()
    return {"csv": csv_bytes, "json": json_bytes, "xlsx": xlsx_bytes}


