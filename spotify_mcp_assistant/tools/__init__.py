"""Thin MCP adapters; domain errors may retain partial progress."""

from spotify_mcp_assistant.spotify_client import SpotifyError


def result(model, function, *args, **kwargs):
    try:
        return model(ok=True, data=function(*args, **kwargs))
    except SpotifyError as error:
        return model(ok=False, data=error.data, error=error.error)
