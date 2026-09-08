from ninja import ModelSchema
from ninja import Query
from ninja import Router

from neuromancers_network.peers.models import PeerProfile
from neuromancers_network.peers.search import search_peers

router = Router(tags=["peers"])


class PeerSearchResultSchema(ModelSchema):
    username: str
    name: str
    languages: list[str]
    tags: list[str]

    class Meta:
        model = PeerProfile
        fields = [
            "bio",
            "is_verified",
        ]

    @staticmethod
    def resolve_username(obj: PeerProfile) -> str:
        return obj.user.username

    @staticmethod
    def resolve_name(obj: PeerProfile) -> str:
        return obj.user.name

    @staticmethod
    def resolve_languages(obj: PeerProfile) -> list[str]:
        return [language.code for language in obj.languages.all()]

    @staticmethod
    def resolve_tags(obj: PeerProfile) -> list[str]:
        return [tag.name for tag in obj.tags.all()]


@router.get("/search/", response=list[PeerSearchResultSchema])
def search_peers_endpoint(
    request,
    languages: str = Query("", description="Comma-separated ISO 639-1 codes."),
    tags: str = Query("", description="Comma-separated tag names."),
):
    lang_codes = [code.strip() for code in languages.split(",") if code.strip()] or None
    tag_names = [name.strip() for name in tags.split(",") if name.strip()] or None
    return search_peers(languages=lang_codes, tags=tag_names).prefetch_related(
        "languages",
        "tags",  # type: ignore[misc]
        "user",
    )
