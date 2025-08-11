import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///recruiting.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    MAIL_FROM = os.getenv("MAIL_FROM", "noreply@example.com")
    MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Recruit Team")
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    LOCAL_STORAGE_DIR = os.getenv("LOCAL_STORAGE_DIR", "./storage")
    S3_ENDPOINT = os.getenv("S3_ENDPOINT")
    S3_BUCKET = os.getenv("S3_BUCKET")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    UID_DOMAIN = os.getenv("UID_DOMAIN", "example.local")