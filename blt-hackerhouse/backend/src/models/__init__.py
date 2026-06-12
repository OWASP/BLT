"""
Domain models for BLT-Hackerhouse.

Every data structure that crosses package boundaries is defined here.
Models have zero internal dependencies — they only import from
pydantic and the Python standard library.
"""

from models.event import Event
from models.contributor import Contributor, ContributorSnapshot
from models.identity import (
    IdentityMapping,
    IdentityFlag,
    PlatformIdentity,
    Platform,
)
from models.room import AvatarState, RoomMapEntry, RoomOccupancy
from models.websocket import (
    SnapshotMessage,
    SnapshotData,
    SnapshotContributor,
    AvatarMoveMessage,
    IdentityFlagMessage,
    IdentityFlagLink,
    IdentityFlagSource,
    LeaderboardUpdateMessage,
)
from models.api import (
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
