from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    import pandas as pd
except ImportError:  # pragma: no cover - optional dep
    pd = None


def file_sha256(file_field_or_path) -> str:
    h = hashlib.sha256()
    if hasattr(file_field_or_path, "chunks"):
        for chunk in file_field_or_path.chunks():
            h.update(chunk)
        file_field_or_path.seek(0)
    else:
        path = Path(file_field_or_path)
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    return h.hexdigest()


def normalize_course(code: str) -> str:
    if not code:
        return ""
    return str(code).replace(" ", "").upper().strip()


def is_valid_cell(cell: Any) -> bool:
    if pd.isna(cell):
        return False
    text = str(cell).strip().lower()

    if not text or text == "nan" or "exam schedule" in text or "mid-term" in text or "final exam" in text:
        return False

    return True


TEACHER_NAME_MAP: dict[str, str] = {}


def resolve_teacher_name(short: str) -> str:
    key = (short or "").strip()
    if not key:
        return ""
    return TEACHER_NAME_MAP.get(key.upper(), key)


CODE_ALIASES = frozenset(
    {"course code", "code", "course_code", "coursecode", "c.code", "ccode"}
)
NAME_ALIASES = frozenset(
    {
        "course name",
        "name",
        "course_name",
        "title",
        "course title",
        "c.name",
    }
)
DATE_ALIASES = frozenset(
    {"exam date", "date", "exam_date", "day", "schedule date"}
)
TIME_ALIASES = frozenset({"time", "exam time", "exam_time", "slot"})
ROOM_ALIASES = frozenset({"room", "venue", "hall", "center"})

COURSE_CELL_RE = re.compile(
    r"^\s*(?P<code>[A-Za-z]{3}\s*\d{3,4})\s*-\s*(?P<section>[^-]+)\s*-\s*(?P<room>[^-]+)\s*-\s*(?P<faculty>.+)$"
)


def _norm_col(c: Any) -> str:
    return re.sub(r"\s+", " ", str(c).strip().lower())


def _pick_column(columns: list[str], aliases: frozenset) -> str | None:
    normalized = {_norm_col(c): c for c in columns}
    for key, original in normalized.items():
        if key in aliases:
            return original
    for key, original in normalized.items():
        if any(alias in key for alias in aliases):
            return original
    return None


def _parse_date(val: Any) -> date | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val

    s = str(val).replace("\n", " ").strip()
    if not s:
        return None

    match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)
    if match:
        d, m, y = match.groups()
        try:
            return date(int(y), int(m), int(d))
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        ts = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.isna(ts):
            return None
        return ts.date()
    except Exception:
        return None


def _infer_columns_from_data(df: pd.DataFrame) -> tuple[str | None, str | None]:
    if df.empty:
        return None, None

    candidate_course_col: str | None = None
    candidate_date_col: str | None = None
    best_course_score = 0
    best_date_score = 0

    for col in df.columns:
        series = df[col]
        non_na = series.dropna()
        if non_na.empty:
            continue

        sample = non_na.head(40)

        course_score = 0
        for v in sample:
            s = str(v).strip()
            if not s:
                continue
            if COURSE_CELL_RE.match(s) or re.search(r"[A-Za-z]{3}\s*\d{3,4}", s):
                course_score += 1

        if course_score > best_course_score and course_score >= 3:
            best_course_score = course_score
            candidate_course_col = col

        date_score = 0
        for v in sample:
            if _parse_date(v) is not None:
                date_score += 1

        if date_score > best_date_score and date_score >= 3:
            best_date_score = date_score
            candidate_date_col = col

    return candidate_course_col, candidate_date_col


def _split_course_cell(raw: str) -> tuple[str, str, str, str]:
    s = str(raw or "").strip()
    if not s:
        return "", "", "", ""

    parts = [p.strip() for p in s.split('-')]

    if len(parts) < 4:
        m2 = re.search(r"[A-Za-z]{3}\s*\d{3,4}", s)
        code = normalize_course(m2.group(0)) if m2 else normalize_course(s)
        return code, "", "", ""

    faculty = parts[-1]
    room = parts[-2]
    section = parts[-3]

    course_part = "-".join(parts[:-3]).strip()

    primary_code_raw = course_part.split('/')[0].strip()

    if not primary_code_raw and '/' in course_part:
        primary_code_raw = course_part.split('/')[1].strip()

    code = normalize_course(primary_code_raw)

    return code, section, room, faculty


def _parse_tabular_excel(path: str | Path) -> list[dict[str, Any]]:
    df = pd.read_excel(path, engine="openpyxl")
    if df.empty:
        return []

    cols = [str(c) for c in df.columns]
    code_col = _pick_column(cols, CODE_ALIASES)
    name_col = _pick_column(cols, NAME_ALIASES)
    date_col = _pick_column(cols, DATE_ALIASES)
    time_col = _pick_column(cols, TIME_ALIASES)
    room_col = _pick_column(cols, ROOM_ALIASES)
    section_col = _pick_column(cols, frozenset({"section", "sec", "class"}))
    faculty_col = _pick_column(cols, frozenset({"faculty", "teacher", "instructor", "lecturer"}))

    inferred_code, inferred_date = _infer_columns_from_data(df)
    code_col = code_col or inferred_code
    date_col = date_col or inferred_date
    if not code_col or not date_col:
        return []

    rows_out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        exam_date = _parse_date(row.get(date_col))
        if exam_date is None:
            continue
        raw_code = row.get(code_col)
        if not is_valid_cell(raw_code):
            continue
        code, section, room, faculty = _split_course_cell(str(raw_code))
        if not code:
            code = normalize_course(str(raw_code))
        if section_col and is_valid_cell(row.get(section_col)):
            section = str(row.get(section_col)).strip()
        if room_col and is_valid_cell(row.get(room_col)):
            room = str(row.get(room_col)).strip()
        if faculty_col and is_valid_cell(row.get(faculty_col)):
            faculty = str(row.get(faculty_col)).strip()
        course_name = code
        if name_col and is_valid_cell(row.get(name_col)):
            course_name = str(row.get(name_col)).strip()
        exam_time = ""
        if time_col and is_valid_cell(row.get(time_col)):
            exam_time = str(row.get(time_col)).strip()
        if not code:
            continue
        rows_out.append({
            "course_code": code.upper().strip(),
            "section": section.strip(),
            "room": room.strip(),
            "faculty": faculty.strip(),
            "exam_date": exam_date,
            "exam_time": exam_time,
            "course_name": course_name,
        })
    return rows_out


def parse_routine_excel(path: str | Path) -> list[dict[str, Any]]:
    if pd is None:
        raise RuntimeError("Install pandas and openpyxl to import exam routines.")

    df = pd.read_excel(path, engine="openpyxl", header=None)
    if df.empty:
        return []

    header_row_idx = -1
    for i, row in df.iterrows():
        row_str = " ".join(str(val).lower() for val in row if not pd.isna(val))
        if (("day" in row_str or "date" in row_str) and "time" in row_str) or (
            "am" in row_str and "pm" in row_str
        ):
            header_row_idx = i
            break

    if header_row_idx == -1:
        return _parse_tabular_excel(path)

    header_row = df.iloc[header_row_idx]
    time_slots = []
    current_time_slot = None
    for val in header_row[1:]:
        if is_valid_cell(val):
            current_time_slot = str(val).strip()
        time_slots.append(current_time_slot)

    rows_out: list[dict[str, Any]] = []
    current_date = None

    for i in range(header_row_idx + 1, len(df)):
        date_raw = df.iloc[i, 0]
        parsed_date = _parse_date(date_raw)

        if parsed_date:
            current_date = parsed_date

        if current_date is None:
            continue

        for j, time_slot in enumerate(time_slots):
            if time_slot is None:
                continue

            cell_val = df.iloc[i, j + 1]
            if not is_valid_cell(cell_val):
                continue

            raw_entries = str(cell_val).split("\n")
            for entry in raw_entries:
                entry = entry.strip()
                if not entry:
                    continue

                code, section, room, faculty = _split_course_cell(entry)
                if not code:
                    continue

                rows_out.append({
                    "course_code": code.upper().strip(),
                    "section": section.strip(),
                    "room": room.strip(),
                    "faculty": faculty.strip(),
                    "exam_date": current_date,
                    "exam_time": time_slot,
                    "course_name": code.upper().strip(),
                })

    return rows_out or _parse_tabular_excel(path)


def link_exams_to_courses(exams_iterable) -> None:
    from users.models import Course

    by_code: dict[str, list[Course]] = {}
    for c in Course.objects.all().only("id", "code"):
        by_code.setdefault(c.code.upper().strip(), []).append(c)

    for exam in exams_iterable:
        key = (exam.course_code or "").upper().strip()
        matches = by_code.get(key, [])
        if len(matches) == 1:
            c = matches[0]
            if exam.course_id != c.id:
                exam.course = c
                exam.save(update_fields=["course"])
