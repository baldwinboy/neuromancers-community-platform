"""
Map Wagtail image filter operations to GetPronto transform parameters.

The original wagtail-cloudinary-image only supported MinMaxOperation.
Here we implement a broader set so that the library can be dropped into
existing Wagtail sites with minimal adjustment.
"""

from typing import TYPE_CHECKING

from wagtail.images.image_operations import FilterOperation
from wagtail.images.image_operations import MinMaxOperation
from wagtail.images.image_operations import WidthHeightOperation

from .getpronto import TransformParams

if TYPE_CHECKING:
    from wagtail.images.models import Filter


def _apply_minmax_operation(
    params: TransformParams,
    operation: MinMaxOperation,
) -> None:

    fit_map = {
        "min": "outside",
        "max": "inside",
    }

    params.fit = fit_map.get(operation.method)
    params.w = operation.width
    params.h = operation.height


def _apply_width_height_operation(
    params: TransformParams,
    operation: WidthHeightOperation,
) -> None:
    fit_map = {
        "fill": "cover",
        "scale": "inside",
        "stretch": "fill",
    }

    params.w = operation.width
    params.h = operation.height

    method = getattr(operation, "method", None)
    if method:
        params.fit = fit_map.get(method)


def _apply_common_operation_params(
    params: TransformParams,
    operation: FilterOperation,
) -> None:
    quality = getattr(operation, "quality", None)
    if quality is not None:
        params.q = quality

    format_ = getattr(operation, "format", None)
    if format_ is not None:
        params.format = format_


def operation_to_transform(
    operation: FilterOperation,
    image_width: int,
    image_height: int,
) -> TransformParams:
    """
    Convert a single Wagtail filter operation into the equivalent
    GetPronto transform parameters.
    """
    params = TransformParams()

    if isinstance(operation, MinMaxOperation):
        _apply_minmax_operation(params, operation)

    elif isinstance(operation, WidthHeightOperation):
        _apply_width_height_operation(params, operation)

    _apply_common_operation_params(params, operation)

    return params


def filter_to_transform_params(
    image_filter: Filter,
    image_width: int,
    image_height: int,
) -> TransformParams:
    """
    Convert a whole Wagtail filter spec ("fill-400x300|format-webp|quality-80")
    into a single set of GetPronto transform parameters.
    """
    merged = TransformParams()
    for operation in image_filter.operations:
        op_params = operation_to_transform(operation, image_width, image_height)
        # Merge: non-None values from op_params overwrite defaults
        for field_name in TransformParams.__dataclass_fields__:
            value = getattr(op_params, field_name)
            if value is not None:
                setattr(merged, field_name, value)
    return merged
