import logging

from bot.telegram_bot import TelegramBot
from common.config import REPOSITORY_SQLITE_DB
from common.repository import SqliteRepository


def setup_logging():
    """配置日志"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logging.getLogger("telegram").setLevel(logging.INFO)


if __name__ == "__main__":
    setup_logging()
    repository = SqliteRepository(REPOSITORY_SQLITE_DB)
    bot = TelegramBot(repository)
    bot.run()
