"""
Lettore XLSX/XLSM minimale e veloce, pensato per il piano turni ATI.

openpyxl impiega 15-30 secondi sul file reale (fogli da 2.600 righe x 80
colonne, stili e calcChain enormi). Qui leggiamo direttamente l'XML del
pacchetto con iterparse, solo le colonne che servono, più i commenti di
cella: su quel file il tempo scende a pochi secondi.

Restituisce solo i valori "cached" (come data_only=True in openpyxl):
le formule non vengono ricalcolate.
"""
from __future__ import annotations

import datetime as dt
import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from xml.etree.ElementTree import iterparse, fromstring

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_M = "{%s}" % NS_MAIN

_REF_RE = re.compile(r"^([A-Z]+)(\d+)$")
_EXCEL_EPOCH = dt.datetime(1899, 12, 30)


def col_index(letters: str) -> int:
    """'A' -> 0, 'H' -> 7, 'AA' -> 26."""
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def col_letters(idx: int) -> str:
    idx += 1
    out = ""
    while idx:
        idx, rem = divmod(idx - 1, 26)
        out = chr(65 + rem) + out
    return out


def cell_ref(row0: int, col0: int) -> str:
    return f"{col_letters(col0)}{row0 + 1}"


def serial_to_date(v) -> dt.date | None:
    """Numero seriale Excel -> date (solo valori plausibili)."""
    if isinstance(v, (int, float)) and 20000 < v < 80000:
        return (_EXCEL_EPOCH + dt.timedelta(days=float(v))).date()
    return None


@dataclass
class Sheet:
    name: str
    path: str
    state: str = "visible"          # visible | hidden | veryHidden
    comments_path: str | None = None


@dataclass
class SheetData:
    rows: list = field(default_factory=list)       # rows[r][c] (0-based), valori grezzi
    comments: dict = field(default_factory=dict)   # (r, c) -> {"t": testo, "a": autore}


class XlsxBook:
    def __init__(self, fileobj):
        self.zf = zipfile.ZipFile(fileobj)
        self._names = set(self.zf.namelist())
        self.sheets: list[Sheet] = []
        self.shared: list[str] = []
        self._load_workbook()
        self._load_shared_strings()

    # ------------------------------------------------------------------ meta
    def _rels(self, part_path: str) -> dict:
        d, f = posixpath.split(part_path)
        rels_path = posixpath.join(d, "_rels", f + ".rels")
        if rels_path not in self._names:
            return {}
        root = fromstring(self.zf.read(rels_path))
        out = {}
        for r in root.iter("{%s}Relationship" % NS_PKG_REL):
            target = r.get("Target", "")
            if target.startswith("/"):
                full = target.lstrip("/")
            else:
                full = posixpath.normpath(posixpath.join(d, target))
            out[r.get("Id")] = (r.get("Type", ""), full)
        return out

    def _load_workbook(self):
        wb_path = "xl/workbook.xml"
        rels = self._rels(wb_path)
        root = fromstring(self.zf.read(wb_path))
        for s in root.iter(_M + "sheet"):
            rid = s.get("{%s}id" % NS_REL)
            typ, path = rels.get(rid, ("", ""))
            if not path or path not in self._names:
                continue
            sh = Sheet(name=s.get("name"), path=path, state=s.get("state") or "visible")
            for typ2, p2 in self._rels(path).values():
                if typ2.endswith("/comments") and p2 in self._names:
                    sh.comments_path = p2
            self.sheets.append(sh)

    def _load_shared_strings(self):
        p = "xl/sharedStrings.xml"
        if p not in self._names:
            return
        with self.zf.open(p) as fh:
            for ev, el in iterparse(fh, events=("end",)):
                if el.tag == _M + "si":
                    self.shared.append("".join(t.text or "" for t in el.iter(_M + "t")))
                    el.clear()

    # ------------------------------------------------------------------ data
    def sheet(self, name: str) -> Sheet | None:
        return next((s for s in self.sheets if s.name == name), None)

    def read(self, sheet: Sheet, max_col: int = 60, max_row: int | None = None,
             with_comments: bool = True) -> SheetData:
        """Legge le prime `max_col` colonne del foglio (0-based esclusivo)."""
        data = SheetData()
        rows = data.rows
        shared = self.shared
        tag_row, tag_c, tag_v, tag_is, tag_t = _M + "row", _M + "c", _M + "v", _M + "is", _M + "t"

        with self.zf.open(sheet.path) as fh:
            cur = None
            cur_r = -1
            for ev, el in iterparse(fh, events=("start", "end")):
                tag = el.tag
                if ev == "start":
                    if tag == tag_row:
                        rr = el.get("r")
                        cur_r = int(rr) - 1 if rr else cur_r + 1
                        if max_row is not None and cur_r >= max_row:
                            break
                        while len(rows) < cur_r:
                            rows.append([])
                        cur = []
                        rows.append(cur)
                        cur_col = -1
                    continue
                # end events
                if tag == tag_c:
                    ref = el.get("r")
                    if ref:
                        m = _REF_RE.match(ref)
                        c = col_index(m.group(1)) if m else cur_col + 1
                    else:
                        c = cur_col + 1
                    cur_col = c
                    if c < max_col:
                        t = el.get("t")
                        val = None
                        if t == "inlineStr":
                            is_ = el.find(tag_is)
                            if is_ is not None:
                                val = "".join(x.text or "" for x in is_.iter(tag_t))
                        else:
                            v = el.find(tag_v)
                            if v is not None and v.text is not None:
                                txt = v.text
                                if t == "s":
                                    try:
                                        val = shared[int(txt)]
                                    except (ValueError, IndexError):
                                        val = None
                                elif t in ("str", "e"):
                                    val = txt
                                elif t == "b":
                                    val = txt == "1"
                                else:
                                    try:
                                        f = float(txt)
                                        val = int(f) if f.is_integer() else f
                                    except ValueError:
                                        val = txt
                        if val is not None and cur is not None:
                            if len(cur) <= c:
                                cur.extend([None] * (c + 1 - len(cur)))
                            cur[c] = val
                    el.clear()
                elif tag == tag_row:
                    el.clear()

        if with_comments and sheet.comments_path:
            data.comments = self._read_comments(sheet.comments_path, max_col)
        return data

    def _read_comments(self, path: str, max_col: int) -> dict:
        root = fromstring(self.zf.read(path))
        authors = [a.text or "" for a in root.iter(_M + "author")]
        out = {}
        for cm in root.iter(_M + "comment"):
            m = _REF_RE.match(cm.get("ref", ""))
            if not m:
                continue
            c = col_index(m.group(1))
            r = int(m.group(2)) - 1
            if c >= max_col:
                continue
            text_el = cm.find(_M + "text")
            txt = "".join(t.text or "" for t in text_el.iter(_M + "t")) if text_el is not None else ""
            try:
                author = authors[int(cm.get("authorId", "-1"))]
            except (ValueError, IndexError):
                author = ""
            out[(r, c)] = {"t": txt, "a": author}
        return out
