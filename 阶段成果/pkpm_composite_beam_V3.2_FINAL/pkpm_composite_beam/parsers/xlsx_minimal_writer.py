"""
Minimal XLSX writer (stdlib-only).

Purpose:
- Allow UI to generate a temporary Excel file without `openpyxl`.
- The generated XLSX is a simple workbook with table-like sheets:
  first row headers + subsequent data rows.

Notes:
- Writes values as numbers when possible, otherwise as inline strings.
- No styles, no formulas, no merged cells.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import zipfile
import xml.etree.ElementTree as ET


_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKGREL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _a1(col: int, row: int) -> str:
    x = col
    letters = ""
    while x > 0:
        x, r = divmod(x - 1, 26)
        letters = chr(ord("A") + r) + letters
    return f"{letters}{row}"


def _to_number(v: Any) -> Tuple[bool, str]:
    if v is None:
        return False, ""
    if isinstance(v, bool):
        return True, "1" if v else "0"
    if isinstance(v, (int, float)):
        return True, str(v)
    s = str(v).strip()
    if s == "":
        return False, ""
    try:
        # keep ints without decimal
        if "." in s or "e" in s.lower():
            float(s)
            return True, s
        int(s)
        return True, s
    except Exception:
        return False, s


def _worksheet_xml(headers: List[str], rows: List[Dict[str, Any]]) -> bytes:
    ET.register_namespace("", _MAIN_NS)
    ws = ET.Element(f"{{{_MAIN_NS}}}worksheet")
    sheet_data = ET.SubElement(ws, f"{{{_MAIN_NS}}}sheetData")

    def add_row(r_idx: int, values: List[Any]):
        row_el = ET.SubElement(sheet_data, f"{{{_MAIN_NS}}}row", {"r": str(r_idx)})
        for c_idx, v in enumerate(values, start=1):
            is_num, sval = _to_number(v)
            if sval == "" and v is None:
                continue
            cell_attrs = {"r": _a1(c_idx, r_idx)}
            c = ET.SubElement(row_el, f"{{{_MAIN_NS}}}c", cell_attrs)
            if is_num:
                v_el = ET.SubElement(c, f"{{{_MAIN_NS}}}v")
                v_el.text = sval
            else:
                c.set("t", "inlineStr")
                is_el = ET.SubElement(c, f"{{{_MAIN_NS}}}is")
                t_el = ET.SubElement(is_el, f"{{{_MAIN_NS}}}t")
                t_el.text = sval

    add_row(1, headers)
    for i, row in enumerate(rows, start=2):
        add_row(i, [row.get(h) for h in headers])

    return ET.tostring(ws, encoding="utf-8", xml_declaration=True)


def write_table_workbook(xlsx_path: str, sheets: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    sheets: {sheet_name: [row_dict, ...]}
    """
    # Build headers per sheet (union, keep insertion order from first row)
    sheet_items = []
    for name, rows in sheets.items():
        headers: List[str] = []
        seen = set()
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    headers.append(k)
                    seen.add(k)
        sheet_items.append((name, headers, rows))

    # [Content_Types].xml
    types = ET.Element(
        "Types",
        {
            "xmlns": "http://schemas.openxmlformats.org/package/2006/content-types",
        },
    )
    ET.SubElement(types, "Default", {"Extension": "xml", "ContentType": "application/xml"})
    ET.SubElement(types, "Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    ET.SubElement(types, "Override", {"PartName": "/xl/workbook.xml", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"})
    for i in range(1, len(sheet_items) + 1):
        ET.SubElement(
            types,
            "Override",
            {
                "PartName": f"/xl/worksheets/sheet{i}.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
            },
        )
    content_types_xml = ET.tostring(types, encoding="utf-8", xml_declaration=True)

    # _rels/.rels
    rels = ET.Element("Relationships", {"xmlns": _PKGREL_NS})
    ET.SubElement(
        rels,
        "Relationship",
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
            "Target": "xl/workbook.xml",
        },
    )
    root_rels_xml = ET.tostring(rels, encoding="utf-8", xml_declaration=True)

    # xl/workbook.xml
    ET.register_namespace("", _MAIN_NS)
    ET.register_namespace("r", _REL_NS)
    wb = ET.Element(f"{{{_MAIN_NS}}}workbook")
    sheets_el = ET.SubElement(wb, f"{{{_MAIN_NS}}}sheets")
    for i, (name, _hdr, _rows) in enumerate(sheet_items, start=1):
        ET.SubElement(
            sheets_el,
            f"{{{_MAIN_NS}}}sheet",
            {
                "name": name,
                "sheetId": str(i),
                f"{{{_REL_NS}}}id": f"rId{i}",
            },
        )
    workbook_xml = ET.tostring(wb, encoding="utf-8", xml_declaration=True)

    # xl/_rels/workbook.xml.rels
    wb_rels = ET.Element("Relationships", {"xmlns": _PKGREL_NS})
    for i in range(1, len(sheet_items) + 1):
        ET.SubElement(
            wb_rels,
            "Relationship",
            {
                "Id": f"rId{i}",
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
                "Target": f"worksheets/sheet{i}.xml",
            },
        )
    workbook_rels_xml = ET.tostring(wb_rels, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(xlsx_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml)
        z.writestr("_rels/.rels", root_rels_xml)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        for i, (_name, headers, rows) in enumerate(sheet_items, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _worksheet_xml(headers, rows))

