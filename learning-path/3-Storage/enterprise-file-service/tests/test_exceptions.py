"""Unit tests for custom exceptions."""
import pytest
from fastapi import status
from app.core.exceptions import (
    FileTooLargeError, InvalidMimeTypeError, S3AuthError,
    BucketUnavailableError, FileRecordNotFoundError,
)


def test_file_too_large():
    exc = FileTooLargeError(max_mb=10)
    assert exc.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert "10 MB" in exc.detail


def test_invalid_mime():
    exc = InvalidMimeTypeError("video/mp4", ["image/png"])
    assert exc.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert "video/mp4" in exc.detail


def test_s3_auth_error():
    exc = S3AuthError()
    assert exc.status_code == status.HTTP_401_UNAUTHORIZED


def test_bucket_unavailable():
    exc = BucketUnavailableError("my-bucket")
    assert exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "my-bucket" in exc.detail


def test_file_record_not_found():
    exc = FileRecordNotFoundError("uuid-123")
    assert exc.status_code == status.HTTP_404_NOT_FOUND
    assert "uuid-123" in exc.detail
