# Manifest

Generated with [https://github.com/phalt/clientele](https://github.com/phalt/clientele)

Install with pip:

```sh
pip install clientele
```

Or with uv:

```sh
uv add clientele
```

API VERSION: 1.1.1
OPENAPI VERSION: 3.0.3
CLIENTELE VERSION: 2.3.1

Regenerate using this command (upstream spec is the source of truth):

```sh
uv run clientele start-api -u https://docs.daily.co/openapi.json -o daily --regen
```

Post-generation compatibility patch: clientele 2.3.1 emits
`DailyStreamingLayoutConfig` with a `preset` discriminator whose members use
`str`, which pydantic 2.13 rejects at import time. After regenerating, replace
the annotated union in `daily/schemas.py` with a plain union of the five
`DailyStreaming*LayoutConfig` classes (no `pydantic.Field(discriminator=...)`).
The affected streaming models are unused by this project.
