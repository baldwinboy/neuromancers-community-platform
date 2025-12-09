from decimal import ROUND_HALF_UP, Decimal

from django import forms
from django.core.validators import MinValueValidator
from django.utils.translation import gettext as _


class GroupedFormMixin:
    field_groups = []

    def get_field_groups(self):
        return [
            (group_title, [self[field_name] for field_name in field_list])
            for group_title, field_list in self.field_groups
        ]


class PriceFormMixin:
    price = forms.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0, message=_("Cannot charge negative values"))],
    )
    concessionary_price = forms.DecimalField(
        required=False,
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0, message=_("Cannot charge negative values"))],
    )

    def clean_price(self):
        data = self.cleaned_data["price"]

        if not data:
            return data

        return int(data * 100)

    def clean_concessionary_price(self):
        data = self.cleaned_data["concessionary_price"]

        if not data:
            return data

        return int(data * 100)


class InitialPriceFormMixin:
    price_fields = ("price", "concessionary_price")
    cents_factor = Decimal(100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not (self.instance and self.instance.pk):
            return

        for field in self.price_fields:
            raw = getattr(self.instance, field, None)
            if raw is None:
                continue

            decimal_value = (Decimal(raw) / self.cents_factor).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            self.initial[field] = decimal_value


class PublishFormMixin:
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.is_published = not instance.is_published
        if commit:
            instance.save()
        return instance
        return instance
