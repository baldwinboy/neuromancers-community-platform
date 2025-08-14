from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from guardian.admin import GuardedModelAdmin

from .models import User, UserGroup


class GuardedUserAdmin(UserAdmin, GuardedModelAdmin):
    pass


class GuardedGroupAdmin(GroupAdmin, GuardedModelAdmin):
    pass


# Register your models here.
admin.site.register(User, GuardedUserAdmin)
admin.site.register(UserGroup, GuardedGroupAdmin)
