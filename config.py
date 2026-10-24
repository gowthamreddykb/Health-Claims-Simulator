import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-health-claims-sim-2026")
    
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "gowtham@69")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "health_insurance_claims")
    
    # Safely handle special characters in password
    escaped_password = quote_plus(DB_PASSWORD) if DB_PASSWORD else ""
    auth_part = f"{DB_USER}:{escaped_password}@" if DB_PASSWORD else f"{DB_USER}@"
    
    # Support MySQL with fallback to SQLite for local development or CI testing
    DEFAULT_MYSQL_URI = f"mysql+pymysql://{auth_part}{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "mysql+mysqlconnector://root:gowtham%4069@127.0.0.1:3306/health_insurance_claims")

    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }
    
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = False
    WTF_CSRF_TIME_LIMIT = None
    
    # Secure document uploads
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB limit

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
