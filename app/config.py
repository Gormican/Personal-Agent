import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    timezone: str = os.getenv("APP_TIMEZONE", "America/Los_Angeles")
    city: str = os.getenv("CITY", "San Diego")

settings = Settings()
