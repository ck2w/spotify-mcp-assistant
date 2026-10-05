"""Atomic private writes and bounded cross-process token-cache locking."""

import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from spotify_mcp_assistant.setup_types import LockTimeoutError


def secure_private_directory(directory: Path) -> None:
    if directory.is_symlink():
        raise OSError("Private directory must not be a symlink")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)


def atomic_private_write(path: Path, content: bytes) -> None:
    if path.is_symlink():
        raise OSError("Private file must not be a symlink")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            os.fchmod(file.fileno(), 0o600)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        if path.is_symlink():
            raise OSError("Private file must not be a symlink")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def token_lock(directory: Path, *, timeout: float = 20.0):
    secure_private_directory(directory)
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(directory / ".token.lock", flags, 0o600)
    os.fchmod(fd, 0o600)
    try:
        if os.name == "nt":
            import msvcrt

            if os.fstat(fd).st_size == 0:
                os.write(fd, b"0")

            def acquire():
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)

            def release():
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            def acquire():
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            def release():
                fcntl.flock(fd, fcntl.LOCK_UN)

        deadline = time.monotonic() + timeout
        while True:
            try:
                acquire()
                break
            except (BlockingIOError, PermissionError):
                if time.monotonic() >= deadline:
                    raise LockTimeoutError() from None
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            release()
    finally:
        os.close(fd)
