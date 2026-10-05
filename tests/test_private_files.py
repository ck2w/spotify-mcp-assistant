import multiprocessing
from pathlib import Path

import pytest


def hold_lock(directory, ready, release):
    from spotify_mcp_assistant.private_files import token_lock

    with token_lock(Path(directory)):
        ready.set()
        release.wait(5)


def test_private_write_permissions(tmp_path):
    from spotify_mcp_assistant.private_files import atomic_private_write, secure_private_directory

    directory = tmp_path / "private"
    secure_private_directory(directory)
    atomic_private_write(directory / "secret", b"fake")
    assert directory.stat().st_mode & 0o777 == 0o700
    assert (directory / "secret").stat().st_mode & 0o777 == 0o600
    assert (directory / "secret").read_bytes() == b"fake"


def test_failed_replace_preserves_original(tmp_path, monkeypatch):
    from spotify_mcp_assistant import private_files

    target = tmp_path / "secret"
    target.write_bytes(b"old")
    monkeypatch.setattr(private_files.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("failure")))
    with pytest.raises(OSError):
        private_files.atomic_private_write(target, b"new")
    assert target.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [target]


def test_lock_blocks_other_process_and_times_out(tmp_path):
    from spotify_mcp_assistant.private_files import token_lock
    from spotify_mcp_assistant.setup_types import LockTimeoutError

    ctx = multiprocessing.get_context("spawn")
    ready, release = ctx.Event(), ctx.Event()
    proc = ctx.Process(target=hold_lock, args=(str(tmp_path), ready, release))
    proc.start()
    try:
        assert ready.wait(5)
        with pytest.raises(LockTimeoutError):
            with token_lock(tmp_path, timeout=0.05):
                pytest.fail("entered occupied lock")
    finally:
        release.set()
        proc.join(5)
        if proc.is_alive():
            proc.terminate()
            proc.join()
    assert proc.exitcode == 0
    with token_lock(tmp_path, timeout=0.1):
        pass


def test_lock_released_after_exception(tmp_path):
    from spotify_mcp_assistant.private_files import token_lock

    with pytest.raises(RuntimeError):
        with token_lock(tmp_path):
            raise RuntimeError("stop")
    with token_lock(tmp_path, timeout=0.1):
        pass


def test_reject_symlink_private_file(tmp_path):
    from spotify_mcp_assistant.private_files import atomic_private_write

    original = tmp_path / "original"
    original.write_bytes(b"keep")
    target = tmp_path / "secret"
    target.symlink_to(original)
    with pytest.raises(OSError):
        atomic_private_write(target, b"new")
    assert original.read_bytes() == b"keep"
