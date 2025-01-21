import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

WALLHAVEN_API_KEY = os.getenv("WALLHAVEN_API_KEY", "")

REPOSITORY_SQLITE_DB = os.getenv("REPOSITORY_SQLITE_DB", os.path.join(os.getcwd(), "iwallpapers.db"))

SPIDER_STORE_DIR = os.getenv("SPIDER_STORE_DIR", os.path.join(os.getcwd()))

PROXY = os.getenv("PROXY", "")


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

CIVITAI_API_KEY = os.getenv("CIVITAI_API_KEY", "")

POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")
