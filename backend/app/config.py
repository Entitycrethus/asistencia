import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    NGROK_AUTHTOKEN: str = os.getenv("NGROK_AUTHTOKEN", "")
    NGROK_PUBLIC_URL: str = ""
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "asistencia-secret-key-2026-fastapi")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    @property
    def is_db_configured(self) -> bool:
        return (
            bool(self.DATABASE_URL)
            and "[YOUR-PASSWORD]" not in self.DATABASE_URL
            and "[TU-PASSWORD]" not in self.DATABASE_URL
        )


settings = Settings()
