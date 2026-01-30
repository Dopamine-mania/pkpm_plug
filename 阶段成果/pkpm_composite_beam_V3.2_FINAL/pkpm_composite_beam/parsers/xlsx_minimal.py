"""
Minimal XLSX reader (stdlib-only).

Purpose:
- Provide a fallback when `openpyxl` is not available.
- Support this project's simple "table" sheets (header row + data rows).

Limitations:
- Reads only cell values (numbers/strings/bools).
- Does not evaluate formulas (returns the stored value if present).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import zipfile
import xml.etree.ElementTree as ET
import re


_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _col_to_index(col: str) -> int:
    idx = 0
    for ch in col:
        idx = idx * 26 + (ord(ch.upper()) - ord("A") + 1)
    return idx


_CELL_REF_RE = re.compile(r"^([A-Za-z]+)(\d+)$")


def _cell_ref_to_rc(cell_ref: str) -> Tuple[int, int]:
    m = _CELL_REF_RE.match(cell_ref)
    if not m:
        raise ValueError(f"invalid cell ref: {cell_ref}")
    c = _col_to_index(m.group(1))
    r = int(m.group(2))
    return r, c


def _parse_shared_strings(z: zipfile.ZipFile) -> List[str]:
    try:
        data = z.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(data)
    strings: List[str] = []
    for si in root.findall(".//main:si", _NS):
        # Shared string may be rich text (multiple <t> nodes).
        ts = [t.text or "" for t in si.findall(".//main:t", _NS)]
        strings.append("".join(ts))
    return strings


def _workbook_sheet_map(z: zipfile.ZipFile) -> Dict[str, str]:
    """
    Returns: sheet_name -> worksheet_xml_path (e.g. 'xl/worksheets/sheet1.xml')
    """
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target: Dict[str, str] = {}
    for rel in rels.findall("pkgrel:Relationship", _NS):
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rid and target:
            # Targets may be like "worksheets/sheet1.xml" or "/xl/worksheets/sheet1.xml"
            t = target.lstrip("/")
            rid_to_target[rid] = t if t.startswith("xl/") else ("xl/" + t)

    sheet_map: Dict[str, str] = {}
    for sheet in wb.findall(".//main:sheets/main:sheet", _NS):
        name = sheet.attrib.get("name")
        rid = sheet.attrib.get(f"{{{_NS['rel']}}}id")
        if not name or not rid:
            continue
        target = rid_to_target.get(rid)
        if target:
            sheet_map[name] = target
    return sheet_map


def _cell_value(cell: ET.Element, shared: List[str]) -> Any:
    t = cell.attrib.get("t")
    if t == "inlineStr":
        tnode = cell.find(".//main:is/main:t", _NS)
        return (tnode.text or "") if tnode is not None else ""
    v = cell.find("main:v", _NS)
    if v is None:
        return None
    raw = v.text
    if raw is None:
        return None
    if t == "s":
        try:
            return shared[int(raw)]
        except Exception:
            return raw
    if t == "b":
        return raw.strip() in ("1", "true", "TRUE")
    # numeric (or general)
    s = raw.strip()
    if s == "":
        return None
    try:
        if "." in s or "e" in s.lower():
            return float(s)
        return int(s)
    except Exception:
        return s


def read_table_rows(xlsx_path: str, sheet_name: str) -> List[Dict[str, Any]]:
    """
    Reads a simple table sheet:
    - First row is header (strings)
    - Subsequent non-empty rows are data
    """
    with zipfile.ZipFile(xlsx_path, "r") as z:
        sheet_map = _workbook_sheet_map(z)
        sheet_xml = sheet_map.get(sheet_name)
        if not sheet_xml:
            return []
        shared = _parse_shared_strings(z)
        root = ET.fromstring(z.read(sheet_xml))

        # Build sparse map (row,col)->value
        values: Dict[Tuple[int, int], Any] = {}
        for c in root.findall(".//main:sheetData/main:row/main:c", _NS):
            ref = c.attrib.get("r")
            if not ref:
                continue
            try:
                r, col = _cell_ref_to_rc(ref)
            except Exception:
                continue
            values[(r, col)] = _cell_value(c, shared)

        # Determine header row (1)
        headers: List[str] = []
        max_col = 0
        for (r, col), v in values.items():
            if r == 1:
                max_col = max(max_col, col)
        for col in range(1, max_col + 1):
            hv = values.get((1, col))
            if hv is None or str(hv).strip() == "":
                headers.append("")
            else:
                headers.append(str(hv).strip())

        # Data rows: until last row with any value
        max_row = 0
        for (r, _c) in values.keys():
            max_row = max(max_row, r)
        rows: List[Dict[str, Any]] = []
        for r in range(2, max_row + 1):
            row_vals: List[Any] = [values.get((r, c)) for c in range(1, max_col + 1)]
            if all(v is None or (isinstance(v, str) and v.strip() == "") for v in row_vals):
                continue
            d: Dict[str, Any] = {}
            for i, h in enumerate(headers):
                if not h:
                    continue
                d[h] = row_vals[i] if i < len(row_vals) else None
            rows.append(d)
        return rows
