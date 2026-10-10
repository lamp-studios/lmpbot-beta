// Turn a message's image attachments into base64 the AI providers can take.
//
// Everything is capped: a big enough upload would blow the request limit of
// whichever provider is in use (and, on Ollama, the host's memory), so oversized
// or unreadable files are skipped and reported in the text instead. The model is
// told what it couldn't see, which beats it guessing about a missing image.

const IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp", "image/gif"]);

export const MAX_IMAGES = 4;
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
export const MAX_TOTAL_BYTES = 12 * 1024 * 1024;
const DOWNLOAD_TIMEOUT_MS = 20_000;

function mimeOf(attachment) {
  // contentType carries a charset sometimes, and can be missing entirely
  const declared = (attachment.contentType ?? "").split(";")[0].trim().toLowerCase();
  if (declared) return declared;

  const ext = (attachment.name ?? "").split(".").pop()?.toLowerCase();
  if (ext === "png") return "image/png";
  if (ext === "jpg" || ext === "jpeg") return "image/jpeg";
  if (ext === "webp") return "image/webp";
  if (ext === "gif") return "image/gif";
  return "";
}

async function download(url) {
  const res = await fetch(url, { signal: AbortSignal.timeout(DOWNLOAD_TIMEOUT_MS) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return Buffer.from(await res.arrayBuffer());
}

/**
 * Download whatever images a message carries.
 * @param {Iterable<{name?: string, url: string, size?: number, contentType?: string}>} attachments
 * @returns {Promise<{images: Array<{name: string, mimeType: string, data: string}>, notes: string[]}>}
 *   `images` is base64 ready to send; `notes` are lines to append to the prompt
 *   describing what was attached and what had to be skipped.
 */
export async function collectImages(attachments) {
  const images = [];
  const notes = [];
  let totalBytes = 0;

  for (const attachment of attachments ?? []) {
    const name = attachment.name ?? "attachment";
    const mimeType = mimeOf(attachment);

    if (!IMAGE_TYPES.has(mimeType)) {
      notes.push(`[attached file: ${name}${mimeType ? ` (${mimeType})` : ""}, which I can't read]`);
      continue;
    }
    if (images.length >= MAX_IMAGES) {
      notes.push(`[attached image: ${name}, skipped: only ${MAX_IMAGES} images are read per message]`);
      continue;
    }
    if (attachment.size && attachment.size > MAX_IMAGE_BYTES) {
      notes.push(
        `[attached image: ${name}, too large to read ` +
          `(${Math.round(attachment.size / 1024 / 1024)} MB, limit ${MAX_IMAGE_BYTES / 1024 / 1024} MB)]`
      );
      continue;
    }

    let buffer;
    try {
      buffer = await download(attachment.url);
    } catch (err) {
      notes.push(`[attached image: ${name}, which failed to download: ${err?.message ?? err}]`);
      continue;
    }

    // size is what Discord claims; the download is what actually has to be sent
    if (buffer.length > MAX_IMAGE_BYTES || totalBytes + buffer.length > MAX_TOTAL_BYTES) {
      notes.push(`[attached image: ${name}, too large to read]`);
      continue;
    }

    totalBytes += buffer.length;
    images.push({ name, mimeType, data: buffer.toString("base64") });
    notes.push(`[attached image: ${name}]`);
  }

  return { images, notes };
}
