"""Setup contracts. Public results contain no credentials or raw configuration."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ClientName = Literal["claude-desktop", "claude-code", "codex", "cursor"]


class SetupError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class LockTimeoutError(SetupError):
    def __init__(self):
        super().__init__(
            "auth_busy", "Another process is authorizing or refreshing; retry shortly."
        )


@dataclass(frozen=True)
class LaunchSpec:
    command: str
    args: tuple[str, ...]
    config_dir: Path
    version: str


@dataclass(frozen=True)
class MergeResult:
    text: str
    changed: bool
    conflict: bool = False


@dataclass(frozen=True)
class ConfigTarget:
    client: ClientName
    path: Path
    original: bytes | None
    candidate: bytes | None
    status: Literal["ready", "unchanged", "conflict", "invalid"]
    error_code: str | None = None


@dataclass(frozen=True)
class ClientResult:
    client: ClientName
    status: Literal["written", "unchanged", "skipped", "failed"]
    path: Path
    backup: Path | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class CheckResult:
    status: Literal["passed", "failed"]
    code: str | None = None
