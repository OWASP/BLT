"""State layer: room routing for avatar positions."""

from .room_map import ROOM_MAP, DEFAULT_ROOM, resolve_room

__all__ = [
    "ROOM_MAP",
    "DEFAULT_ROOM",
    "resolve_room",
]
