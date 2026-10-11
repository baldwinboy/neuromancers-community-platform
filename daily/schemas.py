from __future__ import annotations

import inspect
import typing

import pydantic
from clientele.schemas import ListResponse  # noqa


class Room(pydantic.BaseModel):
    id: str
    name: str
    api_created: bool | None = None
    privacy: str | None = None
    url: str
    created_at: str | None = None
    config: dict[str, typing.Any] | None = None


class RoomsApplicationJson(pydantic.BaseModel):
    name: str
    privacy: str = "public"
    properties: dict[str, typing.Any]


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
