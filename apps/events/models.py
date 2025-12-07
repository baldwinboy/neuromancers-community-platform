from .models_pages.wagtail_pages import *
from .models_sessions.group import *
from .models_sessions.peer import *

# Lived experiences managed by admins
class LivedExperience(models.Model):
    id = models.CharField(primary_key=True)
    title = models.CharField(max_length=512)
    description = models.TextField(null=True, blank=True, max_length=10_240)

    class Meta:
        ordering = ["title"]


class LivedExperienceGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(LivedExperience, on_delete=models.CASCADE)


# Areas of focus managed by admins
class FocusArea(models.Model):
    id = models.CharField(primary_key=True)
    title = models.CharField(max_length=512)
    description = models.TextField(null=True, blank=True, max_length=10_240)

    class Meta:
        ordering = ["title"]


class FocusAreaGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(FocusArea, on_delete=models.CASCADE)