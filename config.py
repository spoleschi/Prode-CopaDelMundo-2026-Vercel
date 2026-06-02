import os

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")
    ALLOW_EARLY_RESULT_ADMIN = os.getenv("ALLOW_EARLY_RESULT_ADMIN", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
