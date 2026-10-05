from ninja import ModelSchema
from ninja import Query
from ninja import Router

from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.search import search_meetings

router = Router(tags=["meetings"])


class MeetingSearchResultSchema(ModelSchema):
    languages: list[str]
    tags: list[str]

    class Meta:
        model = Meeting
        fields = [
            "id",
            "title",
            "description",
            "meeting_type",
            "pricing_type",
            "price",
            "currency",
            "scheduled_at",
            "status",
        ]

    @staticmethod
    def resolve_languages(obj: Meeting) -> list[str]:
        return [language.code for language in obj.languages.all()]

    @staticmethod
    def resolve_tags(obj: Meeting) -> list[str]:
        return [tag.name for tag in obj.tags.all()]


@router.get("/search/", response=list[MeetingSearchResultSchema])
def search_meetings_endpoint(
    request,
    languages: str = Query("", description="Comma-separated ISO 639-1 codes."),
    tags: str = Query("", description="Comma-separated tag names."),
    countries: str = Query("", description="Comma-separated ISO 3166-1 codes."),
):
    lang_codes = [code.strip() for code in languages.split(",") if code.strip()] or None
    tag_names = [name.strip() for name in tags.split(",") if name.strip()] or None
    country_codes = [
        code.strip() for code in countries.split(",") if code.strip()
    ] or None
    return search_meetings(
        languages=lang_codes,
        tags=tag_names,
        countries=country_codes,
    ).prefetch_related(
        "languages",
        "tags",  # type: ignore[misc]
    )
