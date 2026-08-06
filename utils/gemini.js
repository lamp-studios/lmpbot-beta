import { GoogleGenerativeAI } from "@google/generative-ai";
import { config } from "../config.js";

export const DEFAULT_MODEL = "gemini-2.5-flash";

const genAI = config.geminiApiKey
  ? new GoogleGenerativeAI(config.geminiApiKey)
  : null;

/**
 * Send a prompt to Gemini with optional prior history and images.
 * @param {string} prompt
 * @param {Array<{role: string, parts: Array<{text: string}>}>} history
 * @param {string} [model] overrides the default model
 * @param {Array<{mimeType: string, data: string}>} [images] base64 image data
 * @returns {Promise<string|null>}
 */
export async function chat(prompt, history = [], model = DEFAULT_MODEL, images = []) {
  if (!config.geminiApiKey || !genAI) {
    console.log("[gemini] GEMINI_API_KEY not set");
    return null;
  }

  const parts = [{ text: prompt }];
  for (const { mimeType, data } of images ?? []) {
    parts.push({ inlineData: { mimeType, data } });
  }

  const contents = [...(history ?? []), { role: "user", parts }];

  try {
    const gModel = genAI.getGenerativeModel({ model: model || DEFAULT_MODEL });
    const result = await gModel.generateContent({ contents });
    return result.response.text();
  } catch (err) {
    console.log("[gemini] request exception:", err);
    return null;
  }
}
