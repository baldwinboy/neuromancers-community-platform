"""
Custom Wagtail StreamField blocks with enhanced widgets.
"""

from wagtail import blocks

from apps.core.wagtail_widgets import EmojiPickerWidget


class EmojiChooserBlock(blocks.FieldBlock):
    """
    A block for choosing a single emoji using a visual picker.
    Uses the custom EmojiPickerWidget instead of a dropdown.
    """

    def __init__(self, required=True, help_text=None, **kwargs):
        self.field = blocks.CharBlock(
            required=required,
            help_text=help_text,
            max_length=10,  # Emojis can be multi-codepoint
        ).field
        self.field.widget = EmojiPickerWidget()
        super().__init__(**kwargs)

    class Meta:
        icon = "emoji"
