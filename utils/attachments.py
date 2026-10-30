# Turn a message's image attachments into base64 the AI providers can take.
#
# Everything is capped: a big enough upload would blow the request limit of
# whichever provider is in use (and, on Ollama, the host's memory), so oversized
# or unreadable files are skipped and reported in the text instead. The model is
# told what it couldn't see, which beats it guessing about a missing image.

import asyncio
import base64

import aiohttp

IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

MAX_IMAGES = 4
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 12 * 1024 * 1024
DOWNLOAD_TIMEOUT_S = 20


def _mime_of(attachment) -> str:
    # content_type carries a charset sometimes, and can be missing entirely
    declared = (attachment.content_type or "").split(";")[0].strip().lower()
    if declared:
        return declared

    ext = (attachment.filename or "").rsplit(".", 1)[-1].lower()
    if ext == "png":
        return "image/png"
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    if ext == "webp":
        return "image/webp"
    if ext == "gif":
        return "image/gif"
    return ""


async def _download(session: aiohttp.ClientSession, url: str) -> bytes:
    async with session.get(url) as res:
        if res.status >= 400:
            raise RuntimeError(f"HTTP {res.status}")
        return await res.read()


async def collect_images(attachments):
    """
    Download whatever images a message carries.

    Returns (images, notes): `images` is [{"name", "mime_type", "data"}] with
    base64 data ready to send; `notes` are lines to append to the prompt
    describing what was attached and what had to be skipped.
    """
    images = []
    notes = []
    total_bytes = 0
    attachments = list(attachments or [])
    if not attachments:
        return images, notes

    timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT_S)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attachment in attachments:
            name = attachment.filename or "attachment"
            mime_type = _mime_of(attachment)

            if mime_type not in IMAGE_TYPES:
                notes.append(f"[attached file: {name}{f' ({mime_type})' if mime_type else ''}, which I can't read]")
                continue
            if len(images) >= MAX_IMAGES:
                notes.append(f"[attached image: {name}, skipped: only {MAX_IMAGES} images are read per message]")
                continue
            if attachment.size and attachment.size > MAX_IMAGE_BYTES:
                notes.append(
                    f"[attached image: {name}, too large to read "
                    f"({round(attachment.size / 1024 / 1024)} MB, limit {MAX_IMAGE_BYTES // 1024 // 1024} MB)]"
                )
                continue

            try:
                buffer = await _download(session, attachment.url)
            except Exception as err:
                reason = "timed out" if isinstance(err, asyncio.TimeoutError) else str(err) or type(err).__name__
                notes.append(f"[attached image: {name}, which failed to download: {reason}]")
                continue

            # size is what Discord claims; the download is what actually has to be sent
            if len(buffer) > MAX_IMAGE_BYTES or total_bytes + len(buffer) > MAX_TOTAL_BYTES:
                notes.append(f"[attached image: {name}, too large to read]")
                continue

            total_bytes += len(buffer)
            images.append({"name": name, "mime_type": mime_type, "data": base64.b64encode(buffer).decode("ascii")})
            notes.append(f"[attached image: {name}]")

    return images, notes
