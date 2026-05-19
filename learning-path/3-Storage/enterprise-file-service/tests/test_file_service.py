"""Unit tests for FileService business logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import BackgroundTasks


@pytest.mark.asyncio
async def test_upload_file_success(mock_s3_storage, mock_repo):
    from app.services.file_service import FileService
    from app.core.config import get_settings

    cfg = get_settings()
    session = MagicMock()
    svc = FileService(cfg, session)

    # Inject mocks
    svc._storage = mock_s3_storage
    svc._repo = mock_repo

    file = MagicMock()
    file.filename = "test.pdf"
    file.content_type = "application/pdf"
    file.read = AsyncMock(return_value=b"fake pdf content")

    bg = BackgroundTasks()
    result = await svc.upload_file(file, bg)

    assert result["original_filename"] == "test.pdf"
    assert result["mime_type"] == "application/pdf"
    assert result["status"] == "processing"
    mock_s3_storage.upload_bytes.assert_called_once()
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_get_download_url_success(mock_s3_storage, mock_repo):
    from app.services.file_service import FileService
    from app.core.config import get_settings

    cfg = get_settings()
    session = MagicMock()
    svc = FileService(cfg, session)
    svc._storage = mock_s3_storage
    svc._repo = mock_repo

    result = await svc.get_download_url("test-uuid-1234")

    assert result["file_id"] == "test-uuid-1234"
    assert "presigned" in result["url"]
    assert result["expires_in_seconds"] == cfg.presigned_download_ttl


@pytest.mark.asyncio
async def test_get_download_url_not_found(mock_s3_storage, mock_repo):
    from app.services.file_service import FileService
    from app.core.config import get_settings
    from app.core.exceptions import FileRecordNotFoundError

    cfg = get_settings()
    session = MagicMock()
    svc = FileService(cfg, session)
    svc._storage = mock_s3_storage
    mock_repo.get_by_id = AsyncMock(return_value=None)
    svc._repo = mock_repo

    with pytest.raises(FileRecordNotFoundError):
        await svc.get_download_url("nonexistent-id")


@pytest.mark.asyncio
async def test_list_files(mock_s3_storage, mock_repo):
    from app.services.file_service import FileService
    from app.core.config import get_settings

    cfg = get_settings()
    session = MagicMock()
    svc = FileService(cfg, session)
    svc._storage = mock_s3_storage
    svc._repo = mock_repo

    result = await svc.list_files(limit=10, offset=0)
    assert result["total"] == 1
    assert len(result["items"]) == 1
