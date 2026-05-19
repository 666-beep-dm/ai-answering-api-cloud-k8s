"""pytest fixtures shared across the test suite."""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# Point at in-memory SQLite for unit tests
os.environ.update({
    "ENVIRONMENT": "test",
    "DB_HOST": "localhost", "DB_PORT": "5432",
    "DB_NAME": "test", "DB_USER": "test", "DB_PASSWORD": "test",
    "S3_ACCESS_KEY": "test", "S3_SECRET_KEY": "test",
    "S3_ENDPOINT_URL": "http://localhost:9000",
    "S3_BUCKET_NAME": "test-bucket",
})

from app.core.config import get_settings  # noqa: E402
get_settings.cache_clear()


@pytest.fixture
def mock_s3_storage():
    storage = MagicMock()
    storage.upload_bytes = AsyncMock(return_value={
        "s3_key": "abc123_test.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 1024,
    })
    storage.generate_presigned_download_url = AsyncMock(
        return_value="https://s3.example.com/presigned"
    )
    storage.generate_presigned_upload_url = AsyncMock(
        return_value="https://s3.example.com/presigned-put"
    )
    return storage


@pytest.fixture
def mock_repo():
    from app.models.file_record import FileRecord
    from datetime import datetime
    record = FileRecord(
        id="test-uuid-1234",
        original_filename="test.pdf",
        s3_key="abc123_test.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        status="processing",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    repo = MagicMock()
    repo.create = AsyncMock(return_value=record)
    repo.get_by_id = AsyncMock(return_value=record)
    repo.update_status = AsyncMock()
    repo.list_all = AsyncMock(return_value=[record])
    return repo
