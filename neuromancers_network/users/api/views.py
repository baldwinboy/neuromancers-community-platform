from __future__ import annotations

from typing import TYPE_CHECKING

from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from neuromancers_network.users.api.schema import UpdateUserSchema
from neuromancers_network.users.api.schema import UserSchema
from neuromancers_network.users.models import User

if TYPE_CHECKING:
    from django.db.models import QuerySet

router = Router(tags=["users"])


def _get_users_queryset(request) -> QuerySet[User]:
    return User.objects.filter(pk=request.user.pk)


@router.get("/", response=list[UserSchema])
def list_users(request):
    return _get_users_queryset(request)


@router.get("/me/", response=UserSchema)
def retrieve_current_user(request):
    return request.user


@router.get("/{username}/", response=UserSchema)
def retrieve_user(request, username: str):
    users_qs = _get_users_queryset(request)
    return get_object_or_404(users_qs, username=username)


def _apply_update(user, data: UpdateUserSchema) -> User:
    """Apply identity changes through the same controls as the settings form."""
    from neuromancers_network.users.settings import AccountForm  # noqa: PLC0415

    form = AccountForm(
        data={
            "name": data.name,
            "username": data.username,
            "date_of_birth": user.date_of_birth,
        },
        instance=user,
    )
    if not form.is_valid():
        raise HttpError(400, form.errors.as_text())
    return form.save()


@router.patch("/me/", response=UserSchema)
def update_current_user(request, data: UpdateUserSchema):
    return _apply_update(request.user, data)


@router.patch("/{username}/", response=UserSchema)
def update_user(request, username: str, data: UpdateUserSchema):
    users_qs = _get_users_queryset(request)
    user = get_object_or_404(users_qs, username=username)
    return _apply_update(user, data)
