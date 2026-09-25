import factory
from factory.django import DjangoModelFactory

from neuromancers_network.taxonomy.models import AllowedTag
from neuromancers_network.taxonomy.models import Country
from neuromancers_network.taxonomy.models import TagGroup


class TagGroupFactory(DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Group {n}")

    class Meta:
        model = TagGroup


class AllowedTagFactory(DjangoModelFactory):
    name = factory.Sequence(lambda n: f"tag{n}")
    group = factory.SubFactory(TagGroupFactory)

    class Meta:
        model = AllowedTag


def _country_code(n: int) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return f"{letters[(n // 26) % 26]}{letters[n % 26]}"


class CountryFactory(DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Country {n}")
    code = factory.Sequence(_country_code)

    class Meta:
        model = Country


def ensure_tag(name: str) -> AllowedTag:
    """Return an ``AllowedTag`` named *name*, creating a group if needed."""
    tag = AllowedTag.objects.filter(name=name).first()
    if tag is not None:
        return tag
    return AllowedTag.objects.create(name=name, group=TagGroupFactory())
