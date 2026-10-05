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


class PlaybackState(BaseModel):
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
