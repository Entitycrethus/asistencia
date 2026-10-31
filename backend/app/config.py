import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "asistencia-secret-key-2026-fastapi")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    @property
    def is_supabase_configured(self) -> bool:
        return (
            bool(self.SUPABASE_URL)
            and bool(self.SUPABASE_KEY)
            and "tu-proyecto.supabase.co" not in self.SUPABASE_URL
            and "tu-anon-o-service-role-key" not in self.SUPABASE_KEY
        )


settings = Settings()

