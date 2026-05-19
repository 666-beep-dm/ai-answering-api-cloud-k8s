from fastapi import HTTPException, status


class S3AuthError(HTTPException):
    """Raised when S3 credentials are rejected."""

    def __init__(self, detail: str = "S3 authentication failed. Check your credentials."):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class FileTooLargeError(HTTPException):
    """Raised when the uploaded file exceeds the allowed size limit."""

    def __init__(self, max_mb: int):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the {max_mb} MB limit.",
        )


class BucketUnavailableError(HTTPException):
    """Raised when the target S3 bucket cannot be reached or doesn't exist."""

    def __init__(self, bucket: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"S3 bucket '{bucket}' is unavailable or does not exist.",
        )


class FileNotFoundInStorageError(HTTPException):
    """Raised when the requested file does not exist in the bucket."""

    def __init__(self, filename: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' was not found in storage.",
        )


class InvalidMimeTypeError(HTTPException):
    """Raised when the uploaded file's MIME type is not allowed."""

    def __init__(self, mime: str, allowed: list[str]):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"MIME type '{mime}' is not allowed. Permitted types: {', '.join(allowed)}",
        )
