"""Admin widgets."""

from __future__ import annotations

from django import forms


class SecretInput(forms.PasswordInput):
    """Password input that reveals whether a stored secret exists."""

    def get_context(self, name, value, attrs):
        has_value = bool(value)
        context = super().get_context(name, value, attrs)
        widget = context["widget"]
        widget["attrs"]["data-has-value"] = "true" if has_value else "false"
        widget["attrs"]["placeholder"] = (
            "Stored — leave blank to keep" if has_value else "Not set"
        )
        return context


class ScrollableCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Checkbox list rendered inside a bounded, scrollable container."""

    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault("attrs", {})
        classes = attrs.get("class", "")
        attrs["class"] = " ".join(
            filter(
                None,
                [
                    classes,
                    (
                        "w-flex w-flex-col w-gap-2 w-border "
                        "w-rounded w-p-2 w-overflow-auto "
                        "w-h-52 w-overflow-auto"
                    ),
                ],
            ),
        )
        super().__init__(*args, **kwargs)


class KeyValueWidget(forms.Widget):
    """Edit a mapping as repeated key/value input pairs."""

    template_name = "core/widgets/key_value.html"

    def format_value(self, value):
        if not isinstance(value, dict):
            return []
        return [{"key": key, "value": item} for key, item in value.items()]

    def value_from_datadict(self, data, files, name):
        getlist = getattr(data, "getlist", None)
        if getlist is not None:
            keys = getlist(f"{name}_keys")
            values = getlist(f"{name}_values")
        else:
            raw_keys = data.get(f"{name}_keys", [])
            raw_values = data.get(f"{name}_values", [])
            keys = raw_keys if isinstance(raw_keys, (list, tuple)) else [raw_keys]
            values = (
                raw_values if isinstance(raw_values, (list, tuple)) else [raw_values]
            )
        result = {}
        for raw_key, value in zip(keys, values, strict=False):
            key = (raw_key or "").strip()
            if key:
                result[key] = (value or "").strip()
        return result

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["pairs"] = self.format_value(value)
        return context
