import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://gdelavega:lpdlpslsela@localhost:3306/examlab"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    EXAM_SESSION_HOURS = 24
    EXAM_ENVIRONMENT_START_TIMEOUT_SECONDS = 600
    EXAM_SESSION_CLEANUP_INTERVAL_SECONDS = 30
    PROXMOX_API_URL = os.getenv("PROXMOX_API_URL", "").rstrip("/")
    PROXMOX_API_TOKEN_ID = os.getenv("PROXMOX_API_TOKEN_ID", "")
    PROXMOX_API_TOKEN_SECRET = os.getenv("PROXMOX_API_TOKEN_SECRET", "")
    PROXMOX_NODE = os.getenv("PROXMOX_NODE", "")
    PROXMOX_TEMPLATE_VMID = os.getenv("PROXMOX_TEMPLATE_VMID", "")
    PROXMOX_STORAGE = os.getenv("PROXMOX_STORAGE", "")
    PROXMOX_VERIFY_SSL = os.getenv("PROXMOX_VERIFY_SSL", "true").lower() not in {
        "0",
        "false",
        "no",
    }
    PROXMOX_TIMEOUT_SECONDS = 20
