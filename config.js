import "dotenv/config";

export const config = {
  token: process.env.DANGER_DONTSHARETOYKEN,
  geminiApiKey: process.env.GEMINI_API_KEY,
  mongoUri: process.env.MONGODB_URI,
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseKey: process.env.SUPABASE_KEY,
  kumaPushUrl: process.env.KUMA_PUSH_URL,
  pushgatewayUrl: process.env.PUSHGATEWAY_URL,
  prefix: ".",
};
