from __future__ import annotations

import re

from dsa_tools.errors import ToolExecutionError

_DENY_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bCOPY\b.*\bTO\b",
    r"\bEXPORT\b",
    r"\bIMPORT\b",
    r"\bPRAGMA\b",
    r"\bLOAD\b",
    r";\s*--",
]

_DENY_RE = [re.compile(p, re.IGNORECASE) for p in _DENY_PATTERNS]

_MAX_LEN = 8000
_MAX_ROWS = 10000


def validate_sql(sql: str, max_rows: int = _MAX_ROWS) -> str:
    s = sql.strip()
    if not s:
        raise ToolExecutionError("Empty SQL")
    if len(s) > _MAX_LEN:
        raise ToolExecutionError(f"SQL too long ({len(s)} > {_MAX_LEN})")
    # allow only single statement typically; block multiple statements via semicolon trick
    # but allow trailing semicolon
    stripped = s.rstrip(";").strip()
    if ";" in stripped:
        # multiple statements
        raise ToolExecutionError("Multiple statements not allowed")
    for pat in _DENY_RE:
        if pat.search(s):
            raise ToolExecutionError(f"Disallowed SQL pattern: {pat.pattern!r}")
    # must start with SELECT / WITH / SHOW / DESCRIBE / EXPLAIN
    if not re.match(r"^\s*(SELECT|WITH|SHOW|DESCRIBE|EXPLAIN)\b", s, re.IGNORECASE):
        raise ToolExecutionError("Only read-only SELECT/WITH queries are allowed")
    if max_rows <= 0:
        raise ToolExecutionError("max_rows must be positive")
    return s


def enforce_row_limit(sql: str, max_rows: int) -> str:
    s = sql.rstrip().rstrip(";")
    # if already has LIMIT, keep the smaller
    m = re.search(r"\bLIMIT\s+(\d+)\b", s, re.IGNORECASE)
    if m:
        existing = int(m.group(1))
        if existing <= max_rows:
            return s
        # replace
        return re.sub(r"\bLIMIT\s+\d+\b", f"LIMIT {max_rows}", s, flags=re.IGNORECASE)
    return f"{s} LIMIT {max_rows}"
