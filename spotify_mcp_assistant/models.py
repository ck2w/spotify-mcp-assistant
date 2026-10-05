from typing import Literal

from pydantic import BaseModel


class ErrorInfo(BaseModel):
    code: str
    message: str
    next_action: str
    retryable: bool
    retry_after_seconds: int | None = None


class Device(BaseModel):
    device_id: str | None
    name: str
    type: str
    is_active: bool
    is_restricted: bool


class Track(BaseModel):
    name: str
    artists: list[str]
    track_uri: str
    url: str


class DevicesResult(BaseModel):
    ok: bool
    data: list[Device] | None = None
    error: ErrorInfo | None = None


class SearchResult(BaseModel):
    ok: bool
    data: list[Track] | None = None
    error: ErrorInfo | None = None


class PlaybackTrack(BaseModel):
    name: str
    artists: list[str]
    track_uri: str


class PlaybackDevice(BaseModel):
    device_id: str | None
    name: str
    volume_percent: int | None = None
    supports_volume: bool | None = None


class PlaybackState(BaseModel):
    shuffle_state: bool | None = None
    repeat_state: str | None = None
    context_uri: str | None = None
    has_playback: bool
    is_playing: bool
    progress_ms: int | None
    track: PlaybackTrack | None
    device: PlaybackDevice | None


class PlaybackResult(BaseModel):
    ok: bool
    data: PlaybackState | None = None
    error: ErrorInfo | None = None


class PlayAction(BaseModel):
    status: Literal["preview", "submitted"]
    track_uri: str
    device_id: str
    device_name: str | None = None
    next_action: str


class PlayResult(BaseModel):
    ok: bool
    data: PlayAction | None = None
    error: ErrorInfo | None = None


from typing import Annotated, Any, Generic, TypeVar
from pydantic import Field, StringConstraints

TrackURI = Annotated[str, Field(pattern=r"^spotify:track:[A-Za-z0-9]{22}$")]
PlaylistURI = Annotated[str, Field(pattern=r"^spotify:playlist:[A-Za-z0-9]{22}$")]
PlaylistID = Annotated[str, Field(pattern=r"^[A-Za-z0-9]{22}$")]
DeviceID = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TrackURIs = Annotated[list[TrackURI], Field(min_length=1, max_length=500)]
ReplacementURIs = Annotated[list[TrackURI], Field(max_length=100)]
PageLimit = Annotated[int, Field(ge=1, le=50)]
Offset = Annotated[int, Field(ge=0)]
T = TypeVar("T")


class BusinessResult(BaseModel, Generic[T]):
    ok: bool
    data: T | None = None
    error: ErrorInfo | None = None


class TrackDetail(Track):
    duration_ms: int | None = None
    album: dict[str, str | None] | None = None
    explicit: bool | None = None
    is_playable: bool | None = None


class PlaylistSummary(BaseModel):
    playlist_id: str
    playlist_uri: str
    name: str
    url: str
    owner_id: str | None = None
    public: bool | None = None
    collaborative: bool | None = None
    snapshot_id: str | None = None
    total: int | None = None
    contents_accessible: bool | None = None


class PlaylistEntry(BaseModel):
    position: int
    added_at: str | None = None
    is_local: bool = False
    item_type: str
    track: TrackDetail | None = None


class SavedTrack(BaseModel):
    added_at: str | None = None
    track: TrackDetail | None = None


class Page(BaseModel, Generic[T]):
    items: list[T]
    limit: int
    offset: int
    total: int | None = None
    has_more: bool
    next_offset: int | None = None


class MutationData(BaseModel):
    operation: str
    status: Literal["preview", "submitted", "partial", "unknown"]
    target: dict[str, str]
    parameters: dict[str, Any]
    requested_count: int
    submitted_count: int
    snapshot_id: str | None = None
    next_action: str
    normalized_uris: list[str] = Field(default_factory=list)
    input_indices: list[list[int]] = Field(default_factory=list)
    submitted_ranges: list[tuple[int, int]] = Field(default_factory=list)
    failed_range: tuple[int, int] | None = None
    unknown_range: tuple[int, int] | None = None
    not_attempted_ranges: list[tuple[int, int]] = Field(default_factory=list)
    playlist_id: str | None = None
    playlist_uri: str | None = None
    url: str | None = None


class SavedCheck(BaseModel):
    track_uri: str
    saved: bool


class SavedCheckData(BaseModel):
    items: list[SavedCheck]
    unqueried_uris: list[str] = Field(default_factory=list)


class QueueEntry(BaseModel):
    item_type: str
    track: TrackDetail | None = None


class QueueData(BaseModel):
    currently_playing: QueueEntry | None = None
    queue: list[QueueEntry]


def normalize_uris(uris: list[str], *, deduplicate: bool) -> tuple[list[str], list[list[int]]]:
    normalized, indices, seen = [], [], {}
    for index, uri in enumerate(uris):
        if deduplicate and uri in seen:
            indices[seen[uri]].append(index)
        else:
            seen[uri] = len(normalized)
            normalized.append(uri)
            indices.append([index])
    return normalized, indices
