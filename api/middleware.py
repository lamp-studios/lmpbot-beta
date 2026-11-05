import hmac

from aiohttp import web

from api.keys import API_KEY
from api.responses import json_error


def public(handler):
    """Mark a route handler as reachable without the API key."""
    handler.public = True
    return handler


def _is_public(request: web.Request) -> bool:
    route = request.match_info.route
    return getattr(route.handler, "public", False) if route is not None else False


def _bearer_token(request: web.Request) -> bytes | None:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip().encode()


@web.middleware
async def auth_middleware(request: web.Request, handler):
    """
    Require `Authorization: Bearer <BOT_API_KEY>` on every route not marked @public.

    Unknown paths are not public either, so an unauthenticated caller gets a 401
    rather than learning which routes exist.
    """
    if _is_public(request):
        return await handler(request)

    token = _bearer_token(request)
    expected = request.app[API_KEY]
    if token is None or not hmac.compare_digest(token, expected):
        return json_error(401, "Unauthorized")
    return await handler(request)


@web.middleware
async def error_middleware(request: web.Request, handler):
    """Turn every error, including aiohttp's own 404/405/413, into a JSON body."""
    try:
        return await handler(request)
    except web.HTTPMethodNotAllowed as exc:
        return json_error(405, "Method not allowed", headers={"Allow": ",".join(sorted(exc.allowed_methods))})
    except web.HTTPNotFound:
        return json_error(404, "Not found")
    except web.HTTPRequestEntityTooLarge:
        return json_error(413, "Request body too large")
    except web.HTTPException as exc:
        if exc.status < 400:
            raise
        return json_error(exc.status, exc.reason or "Error")
    except Exception as err:
        # method and path only: headers (Authorization) and bodies are never logged
        print(f"[api] {request.method} {request.path} failed: {err!r}")
        return json_error(500, "Internal server error")
