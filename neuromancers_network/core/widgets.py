"""Admin widgets."""

from __future__ import annotations

from django import forms


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
