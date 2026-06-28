import os
from dotenv import load_dotenv

load_dotenv()

# ── Meta App Config ────────────────────────────────
META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "https://yourdomain.com/oauth/callback")
META_API_VERSION = "v21.0"

# ── App Config ──────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./hanubees.db")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# ── Webhook Config ──────────────────────────────────
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "hanubees_verify_token_123")
