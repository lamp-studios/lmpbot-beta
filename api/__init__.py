"""Authenticated HTTP API for the web dashboard, served in the bot's own process."""

from api.server import start_api, stop_api

__all__ = ["start_api", "stop_api"]
