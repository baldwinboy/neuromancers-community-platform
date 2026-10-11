from __future__ import annotations

from clientele import api as clientele_api

from . import config
from . import schemas

client = clientele_api.APIClient(config=config.Config())


@client.post("/rooms")
def rooms(result: schemas.Room, data: schemas.RoomsApplicationJson) -> schemas.Room:
    """Create a room

    Creates a room. If `name` is omitted (or already taken) Daily generates a unique name. The room is deleted automatically once `exp` is reached.

    """
    return result
