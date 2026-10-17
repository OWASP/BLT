"""
Domain models for BLT-Hackerhouse.

Every data structure that crosses package boundaries is defined here.
Models have zero internal dependencies — they only import from
pydantic and the Python standard library.
"""

from .event import Event
from .contributor import Contributor, ContributorSnapshot
from .identity import (
    IdentityMapping,
    IdentityFlag,
    PlatformIdentity,
    Platform,
)
from .room import AvatarState, RoomMapEntry, RoomOccupancy
from .websocket import (
    SnapshotMessage,
    SnapshotData,
    SnapshotContributor,
    AvatarMoveMessage,
    IdentityFlagMessage,
    IdentityFlagLink,
    IdentityFlagSource,
    LeaderboardUpdateMessage,
)
from .api import (
    PaginatedResponse,
    PaginationMeta,
    ActivityFeedItem,
    LeaderboardEntry,
    StatusResponse,
    StatusData,
    IdentityStats,
    PipelineHealth,
    HealthResponse,
    ComponentHealth,
    StateResponse,
    StateResponseData,
    SnapshotStateContributor,
)

__all__ = [
    # Event
    "Event",
    # Contributor
    "Contributor",
    "ContributorSnapshot",
    # Identity
    "IdentityMapping",
    "IdentityFlag",
    "PlatformIdentity",
    "Platform",
    # Room
    "AvatarState",
    "RoomMapEntry",
    "RoomOccupancy",
    # WebSocket
    "SnapshotMessage",
    "SnapshotData",
    "SnapshotContributor",
    "AvatarMoveMessage",
    "IdentityFlagMessage",
    "IdentityFlagLink",
    "IdentityFlagSource",
    "LeaderboardUpdateMessage",
    # API
    "PaginatedResponse",
    "PaginationMeta",
    "ActivityFeedItem",
    "LeaderboardEntry",
    "StatusResponse",
    "StatusData",
    "IdentityStats",
    "PipelineHealth",
    "HealthResponse",
    "ComponentHealth",
    "StateResponse",
    "StateResponseData",
    "SnapshotStateContributor",
]