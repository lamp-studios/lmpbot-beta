import "dotenv/config";

export const config = {
  token: process.env.DANGER_DONTSHARETOYKEN,
  geminiApiKey: process.env.GEMINI_API_KEY,
  mongoUri: process.env.MONGODB_URI,
  prefix: ".",
};
