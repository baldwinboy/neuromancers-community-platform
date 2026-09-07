from __future__ import annotations

from clientele import api as clientele_api

from . import config
from . import schemas

client = clientele_api.APIClient(config=config.Config())


@client.post("/upload/presign")
def upload_presign(
    result: schemas.UploadPresign200Response,
    data: schemas.UploadPresignApplicationJson,
) -> schemas.UploadPresign200Response:
    """Get a presigned upload URL"""
    return result


@client.post("/upload/confirm")
def upload_confirm(
    result: schemas.UploadConfirm200Response,
    data: schemas.UploadConfirmApplicationJson,
) -> schemas.UploadConfirm200Response:
    """Confirm a file upload"""
    return result


@client.get("/files")
def files(
    result: schemas.Files200Response,
    page: float | None = None,
    page_size: float | None = None,
    folder_name: str | None = None,
) -> schemas.Files200Response:
    """List files"""
    return result


@client.get("/files/{id}")
def files__id_(
    result: schemas.FilesId200Response,
    id: str,  # noqa: A002
) -> schemas.FilesId200Response:
    """Get file metadata"""
    return result


@client.delete("/files/{id}")
def files__id_(result: None, id: str) -> None:  # noqa: A002, F811
    """Delete a file"""
    return result


@client.post("/file/{id}/transform-url")
def file__id__transform_url(
    result: schemas.FileIdTransformUrl200Response,
    data: schemas.FileIdTransformUrlApplicationJson,
    id: str,  # noqa: A002
) -> schemas.FileIdTransformUrl200Response:
    """Get an image transformation URL"""
    return result
