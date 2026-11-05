from aiohttp import web


def json_error(status: int, message: str, **kwargs) -> web.Response:
    """A JSON error body, `{ "error": message }`, with the given status."""
    return web.json_response({"error": message}, status=status, **kwargs)
