from __future__ import annotations

import inspect
import typing

import pydantic
from clientele.schemas import ListResponse  # noqa: F401


class UploadPresign200Response(pydantic.BaseModel):
    upload_url: str = pydantic.Field(alias="uploadUrl")
    pending_upload_id: str = pydantic.Field(alias="pendingUploadId")
    expires_in: float = pydantic.Field(alias="expiresIn")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class UploadPresignApplicationJson(pydantic.BaseModel):
    filename: str
    mimetype: str
    size: float
    custom_filename: str | None = pydantic.Field(
        default=None, alias="customFilename",
    )
    folder_name: str | None = pydantic.Field(default=None, alias="folderName")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class UploadConfirm200Response(pydantic.BaseModel):
    message: str
    file: dict[str, typing.Any]


class UploadConfirmApplicationJson(pydantic.BaseModel):
    pending_upload_id: str = pydantic.Field(alias="pendingUploadId")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Files200Response(pydantic.BaseModel):
    files: list[dict[str, typing.Any]]
    pagination: dict[str, typing.Any]


class FilesId200Response(pydantic.BaseModel):
    id: str
    name: str
    secure_url: str = pydantic.Field(alias="secureUrl")
    secure_thumbnail_url: str = pydantic.Field(alias="secureThumbnailUrl")
    raw_url: str = pydantic.Field(alias="rawUrl")
    type_: str = pydantic.Field(alias="type")
    raw_type: str = pydantic.Field(alias="rawType")
    size: str
    raw_size: float = pydantic.Field(alias="rawSize")
    updated: str
    raw_updated: str = pydantic.Field(alias="rawUpdated")
    folder_id: typing.Any = pydantic.Field(alias="folderId")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class FileIdTransformUrl200Response(pydantic.BaseModel):
    url: str


class FileIdTransformUrlApplicationJson(pydantic.BaseModel):
    w: float
    h: float
    fit: str
    q: float
    blur: float
    sharp: bool
    gray: bool
    rot: float
    border: str
    crop: str
    format: str


def get_subclasses_from_same_file() -> list[type[pydantic.BaseModel]]:
    """
    Due to how Python declares classes in a module,
    we need to update_forward_refs for all the schemas generated
    here in the situation where there are nested classes.
    """
    calling_frame = inspect.currentframe()
    if not calling_frame:
        return []
    calling_frame = calling_frame.f_back
    module = inspect.getmodule(calling_frame)

    subclasses = []
    for _, c in inspect.getmembers(module):
        if (
            inspect.isclass(c)
            and issubclass(c, pydantic.BaseModel)
            and c != pydantic.BaseModel
        ):
            subclasses.append(c)

    return subclasses


subclasses: list[type[pydantic.BaseModel]] = get_subclasses_from_same_file()
for c in subclasses:
    c.model_rebuild()
