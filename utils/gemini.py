import google.generativeai as genai
from config import Config

_model = None


def _get_model():
    global _model
    if _model is None:
        config = Config()
        if not config.gemini_api_key:
            return None
        genai.configure(api_key=config.gemini_api_key)
        _model = genai.GenerativeModel("gemini-2.0-flash")
    return _model


async def chat(prompt: str) -> str | None:
    model = _get_model()
    if model is None:
        return None

    response = await model.generate_content_async(prompt)
    return response.text
