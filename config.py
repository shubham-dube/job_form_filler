import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically load .env if present
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    DEFAULT_PROFILE_PATH: Path = Path(os.getenv("PROFILE_PATH", "profile.md"))
    GOOGLE_COOKIES: str = os.getenv("GOOGLE_COOKIES", "")
    AUTO_OPEN_BROWSER: bool = os.getenv("AUTO_OPEN_BROWSER", "true").lower() in ("1", "true", "yes")

    @classmethod
    def validate_api_key(cls) -> bool:
        return bool(cls.GEMINI_API_KEY and cls.GEMINI_API_KEY != "your_gemini_api_key_here")

config = Config()
