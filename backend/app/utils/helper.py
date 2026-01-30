# app/utils/helper.py

import re

from openpyxl import Workbook

INVALID_SHEET_CHARS = r'[\[\]\:\*\?\/\\]'

def safe_sheet_title(name: str, max_len: int = 31) -> str:
    # Remove invalid Excel characters
    safe = re.sub(INVALID_SHEET_CHARS, '', name)

    # Trim length
    safe = safe.strip()[:max_len]

    # Excel also rejects empty titles
    return safe or "Sheet"

def unique_sheet_title(wb: Workbook, name: str) -> str:
    base = safe_sheet_title(name)
    title = base
    i = 1
    while title in wb.sheetnames:
        suffix = f" ({i})"
        title = base[: 31 - len(suffix)] + suffix
        i += 1
    return title