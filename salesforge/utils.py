from __future__ import annotations

import io
from typing import Any

import pandas as pd
import qrcode
from PIL import Image


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def make_qr_png(data: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img: Image.Image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()


def money(value: Any, currency: str = "USD") -> str:
    try:
        return f"{currency} {float(value):,.0f}"
    except Exception:
        return f"{currency} 0"


def pct(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "0.0%"
