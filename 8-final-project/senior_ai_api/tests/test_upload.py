"""Unit test — /api/v1/upload validation."""
import pytest


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_mime(client):
    resp = await client.post(
        "/api/v1/upload",
        files={"file": ("test.exe", b"binary", "application/octet-stream")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(client):
    big = b"x" * (11 * 1024 * 1024)
    resp = await client.post(
        "/api/v1/upload",
        files={"file": ("big.txt", big, "text/plain")},
    )
    assert resp.status_code == 413
