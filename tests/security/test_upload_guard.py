"""The upload guard has to read the file, not only its name.

`docs/api.md` advertises `upload (multipart, 100MB, MIME sniff, archive bomb guard)`. The last three words
were carried by a parameter nothing read: the route captured a head, threaded it through `save_dataset`, and
`validate_file` accepted `head` and never looked at it. A zip body named `evil.csv` passed -- measured on
2026-10-22 before the fix. The same capture did `tmp_path.read_bytes()[:4096]`, so keeping 4 KiB put a whole
100 MB upload into memory a second time, and the size limit was applied only after the body was fully
written to disk.

Each test below names the case that fails when the guard is removed, and each rejection has a paired
acceptance so the guard cannot be satisfied by rejecting everything.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from dsa_api.core.database import Base, get_session
from dsa_api.main import app
from dsa_api.routers.datasets import HEAD_BYTES, _write_upload_to_temp, create_dataset_route
from dsa_datasets.errors import ValidationError
from dsa_datasets.validate import MAX_SIZE_BYTES, validate_file

REPO = Path(__file__).resolve().parents[2]

ZIP = b"PK\x03\x04"
GZIP = b"\x1f\x8b\x08"
SZ7 = b"7z\xbc\xaf\x27\x1c"
RAR = b"Rar!\x1a\x07"


def _tar_head() -> bytes:
    body = bytearray(300)
    body[257:262] = b"ustar"
    return bytes(body)


# --- the guard reads the leading bytes ---


@pytest.mark.parametrize(
    ("magic", "label"),
    [(ZIP, "zip"), (GZIP, "gzip"), (SZ7, "7z"), (RAR, "rar")],
)
def test_an_archive_signature_under_a_whitelisted_name_is_rejected(
    magic: bytes, label: str
) -> None:
    payload = magic + b"\x00" * 300
    for name in ("evil.csv", "evil.json", "evil.parquet"):
        with pytest.raises(ValidationError, match=f"Archive contents \\({label}\\)"):
            validate_file(name, len(payload), content_type="text/csv", head=payload)


def test_a_tar_header_at_its_own_offset_is_rejected() -> None:
    """`ustar` sits at byte 257 of a tar block, so the guard has to look past the first four bytes."""
    with pytest.raises(ValidationError, match="Archive contents \\(tar\\)"):
        validate_file("evil.csv", 300, content_type="text/csv", head=_tar_head())


def test_xlsx_keeps_the_zip_container_it_is_specified_to_be() -> None:
    """The one exception that keeps this from being a blanket `PK` ban.

    An .xlsx *is* a zip container, so rejecting the signature would reject every real Excel upload. If
    someone simplifies the guard to `if head.startswith(PK): raise`, this is the test that goes red.
    """
    assert validate_file(
        "sheet.xlsx",
        304,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        head=ZIP + b"\x00" * 300,
    )


@pytest.mark.parametrize(
    ("name", "head"),
    [
        ("data.csv", b"a,b\n1,2\n3,4\n"),
        ("data.json", b'[{"a": 1}]'),
        ("data.parquet", b"PAR1\x00\x00"),
    ],
)
def test_an_ordinary_dataset_head_is_not_rejected(name: str, head: bytes) -> None:
    assert validate_file(name, len(head), content_type=None, head=head)


def test_a_caller_that_supplies_no_head_gets_the_name_only_check() -> None:
    """The documented boundary: the API route always has bytes to offer, a CLI reader may not."""
    assert validate_file("local.csv", 8, content_type=None, head=None)


def test_the_extension_blocklist_still_stands_on_its_own() -> None:
    with pytest.raises(ValidationError, match="Archive files not allowed"):
        validate_file("bomb.zip", 100, content_type="application/zip", head=ZIP + b"\x00" * 100)


# --- the head comes off the stream, and the limit is applied during it ---


class _FakeUpload:
    """The part of `UploadFile` the helper uses, with the read count left visible."""

    def __init__(self, filename: str, chunks: list[bytes]) -> None:
        self.filename = filename
        self._chunks = list(chunks)
        self.reads = 0

    async def read(self, size: int) -> bytes:  # the helper asks for 1 MiB; the answer is canned
        self.reads += 1
        return self._chunks.pop(0) if self._chunks else b""

    @property
    def unread_chunks(self) -> int:
        return len(self._chunks)


@pytest.mark.asyncio
async def test_the_head_is_the_first_bytes_of_the_body_without_a_second_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    created: list[str] = []
    real = tempfile.NamedTemporaryFile

    def spy(**kwargs):
        handle = real(**kwargs)
        created.append(handle.name)
        return handle

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", spy)
    payload = b"".join(f"{i},row\n".encode() for i in range(200_000))
    assert len(payload) > 3 * HEAD_BYTES
    chunks = [payload[i : i + 1024 * 1024] for i in range(0, len(payload), 1024 * 1024)]

    path, size, head = await _write_upload_to_temp(_FakeUpload("big.csv", chunks))
    try:
        assert size == len(payload)
        assert len(head) == HEAD_BYTES
        assert head == payload[:HEAD_BYTES]
        assert path.read_bytes() == payload
    finally:
        path.unlink(missing_ok=True)
    assert created and not Path(created[-1]).exists()


@pytest.mark.asyncio
async def test_an_oversized_body_is_refused_without_draining_the_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`MAX_SIZE_BYTES` used to be reached only after every chunk had been written."""
    created: list[str] = []
    real = tempfile.NamedTemporaryFile

    def spy(**kwargs):
        handle = real(**kwargs)
        created.append(handle.name)
        return handle

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", spy)
    body = b"x" * (64 * 1024)
    upload = _FakeUpload("big.csv", [body, body, body, body])
    with pytest.raises(HTTPException) as exc:
        await _write_upload_to_temp(upload, limit=1024)
    assert exc.value.status_code == 400
    assert "too large" in str(exc.value.detail).lower()
    assert upload.reads == 1, (
        f"the refusal pulled {upload.reads} chunks, so the body was still streamed"
    )
    assert upload.unread_chunks == 3
    assert created and not Path(created[-1]).exists(), "the refused upload left a temp file behind"


def test_nobody_opens_the_finished_upload_to_look_at_it() -> None:
    """The head has to stay a by-product of the write, not a second pass over the file.

    `tmp_path.read_bytes()[:4096]` satisfied every assertion above while loading a whole 100 MB upload into
    memory to keep 4 KB of it, so what is pinned here is the shape: neither the helper nor the route may
    call a whole-file reader on the temp path.
    """
    import ast
    import inspect

    for fn in (_write_upload_to_temp, create_dataset_route):
        called = {
            node.func.attr
            for node in ast.walk(ast.parse(inspect.getsource(fn)))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert not called & {"read_bytes", "read_text"}, (
            f"{fn.__name__} re-reads the body: {sorted(called)}"
        )


def test_the_limit_the_docs_promise_is_the_limit_the_code_enforces() -> None:
    """Keyed on the table row's shape, not on the path.

    A later round added a prose bullet that cites the same route to say something else about it, and the
    first-match search this test used to run picked the bullet up and read "100MB" as missing. The row is the
    claim's owner; the path string is not.
    """
    rows = [
        line
        for line in (REPO / "docs/api.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("| POST | `/api/v1/datasets/`")
    ]
    assert len(rows) == 1, f"the upload row must appear exactly once in the route table: {rows}"
    assert "100MB" in rows[0], (
        f"the advertised ceiling no longer matches the enforced one: {rows[0]}"
    )
    assert MAX_SIZE_BYTES == 100 * 1024 * 1024


# --- and the route actually hands those bytes to the guard ---


@pytest.fixture(autouse=True)
async def _clean_limiter():
    """The upload counter is module-level and keyed by client IP, so a full gate run can cross 30/minute."""
    from dsa_api.core.security import clear_rate_limit_state

    await clear_rate_limit_state()
    yield
    await clear_rate_limit_state()


@pytest.fixture
async def ac():
    from dsa_api.core import database

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session():
        async with SessionLocal() as s:
            yield s

    previous = database.AsyncSessionLocal
    database.AsyncSessionLocal = SessionLocal
    app.dependency_overrides[get_session] = _get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    database.AsyncSessionLocal = previous
    await engine.dispose()


@pytest.mark.asyncio
async def test_the_route_refuses_a_zip_that_calls_itself_a_csv(ac: AsyncClient) -> None:
    r = await ac.post(
        "/api/v1/datasets/",
        files={"file": ("renamed.csv", ZIP + b"\x00" * 300, "text/csv")},
    )
    assert r.status_code == 400, r.text
    assert "Archive contents" in r.json()["detail"], r.json()


@pytest.mark.asyncio
async def test_the_route_does_not_refuse_a_real_xlsx_for_being_a_container(ac: AsyncClient) -> None:
    """The guard must not be the thing that rejects Excel -- the bytes are legitimate there.

    A hand-typed `PK` prefix is not a parseable workbook either, so this upload still fails; what it must
    not fail *for* is the archive signature. Asserting the reason is the only way to keep the exception real.
    """
    r = await ac.post(
        "/api/v1/datasets/",
        files={
            "file": (
                "sheet.xlsx",
                ZIP + b"\x00" * 300,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert r.status_code == 400, r.text
    assert "Archive contents" not in r.json()["detail"], r.json()
