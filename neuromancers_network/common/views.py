from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse


def model_form_fields(request, app_label, model):
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model)
    except ContentType.DoesNotExist:
        return JsonResponse({"error": "Not Found"}, status=404)

    model_class = content_type.model_class()
    if not model_class:
        return JsonResponse({"error": "Not Found"}, status=404)

    if not hasattr(model_class, "get_form_fields"):
        return JsonResponse(
            {"error": "Bad request"},
            status=400,
        )

    fields = model_class.get_form_fields()

    if not isinstance(fields, list):
        return JsonResponse({"error": "Bad request"}, status=400)

    return JsonResponse({"fields": fields})
