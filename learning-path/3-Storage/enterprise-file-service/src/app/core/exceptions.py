from fastapi import HTTPException, status


class FileTooLargeError(HTTPException):
    def __init__(self, max_mb: int):
        super().__init__(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                         detail=f"File exceeds {max_mb} MB limit.")


class InvalidMimeTypeError(HTTPException):
    def __init__(self, mime: str, allowed: list[str]):
        super().__init__(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                         detail=f"MIME '{mime}' not allowed. Permitted: {allowed}")


class S3AuthError(HTTPException):
    def __init__(self, detail: str = "S3 authentication failed."):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail=detail)


class S3UploadError(HTTPException):
    def __init__(self, detail: str = "Failed to upload file to storage."):
        super().__init__(status.HTTP_502_BAD_GATEWAY, detail=detail)


class BucketUnavailableError(HTTPException):
    def __init__(self, bucket: str):
        super().__init__(status.HTTP_503_SERVICE_UNAVAILABLE,
                         detail=f"Bucket '{bucket}' unavailable.")


class FileRecordNotFoundError(HTTPException):
    def __init__(self, file_id: str):
        super().__init__(status.HTTP_404_NOT_FOUND,
                         detail=f"File record '{file_id}' not found.")


class StorageKeyNotFoundError(HTTPException):
    def __init__(self, key: str):
        super().__init__(status.HTTP_404_NOT_FOUND,
                         detail=f"Storage key '{key}' not found.")
