import time
import logging
from typing import List
from common.config import REPOSITORY_SQLITE_DB
from common.repository import SqliteRepository
from spiders.spider import Spider
from spiders.spider_wallhaven import WallhavenSpider


def setup_logging():
    """配置日志"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logging.getLogger("pyoctopus").setLevel(logging.INFO)


def run_spiders():
    """执行爬虫任务"""
    logger = logging.getLogger(__name__)
    logger.info("开始执行爬虫任务...")

    try:
        repository = SqliteRepository(REPOSITORY_SQLITE_DB)
        spiders: List[Spider] = [
            WallhavenSpider(repository),
            # ... 其他爬虫实例 ...
        ]

        for spider in spiders:
            spider.run()

        logger.info("爬虫任务执行完成")
    except Exception as e:
        logger.error(f"爬虫任务执行出错: {e}", exc_info=True)


def run_with_delay():
    """执行任务并等待指定时间后再次执行"""
    DELAY_HOURS = 12
    logger = logging.getLogger(__name__)

    while True:
        try:
            # 执行爬虫任务
            run_spiders()

            # 任务执行完成后，等待12小时
            logger.info(f"任务完成，等待{DELAY_HOURS}小时后重新执行...")
            time.sleep(DELAY_HOURS * 3600)  # 转换为秒

        except KeyboardInterrupt:
            logger.info("程序被手动终止")
            break
        except Exception as e:
            logger.error(f"发生错误: {e}", exc_info=True)
            # 发生错误时等待5分钟后继续
            time.sleep(300)


if __name__ == "__main__":
    setup_logging()
    run_with_delay()
