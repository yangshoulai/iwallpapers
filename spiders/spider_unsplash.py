from datetime import datetime
import hashlib
import logging
import os
import time

import requests
from common.config import PROXY, REPOSITORY_SQLITE_DB, SPIDER_STORE_DIR
from common.log import setup_logging
from common.model import Wallpaper
from common.repository import SqliteRepository, WallpaperRepository
from spiders.spider import Spider
import pyoctopus


class UnsplashWallpaper:
    id = pyoctopus.json("$.id")
    src = pyoctopus.json("$.urls.raw")
    source_src = pyoctopus.json("$.links.html")
    description = pyoctopus.json("$.description")
    alt_description = pyoctopus.json("$.alt_description")
    author = pyoctopus.json("$.user.name")
    author_url = pyoctopus.json("$.user.links.html")
    colors = pyoctopus.json("$.color", multi=True)
    width = pyoctopus.json("$.width", converter=pyoctopus.int_converter(0))
    height = pyoctopus.json("$.height", converter=pyoctopus.int_converter(0))


class UnsplashPageListResponse:
    wallpapers = pyoctopus.embedded(pyoctopus.json("$.[*]", multi=True), UnsplashWallpaper)


class UnsplashSpider(Spider):
    def __init__(self, repository: WallpaperRepository):
        super().__init__(repository)

    def run(self):
        seeds = [
            pyoctopus.request(
                f"https://unsplash.com/napi/topics/wallpapers/photos?page={i}&per_page=10",
                priority=1,
                headers={"Accept": "application/json"},
            )
            for i in range(1, 10)
        ]
        store = pyoctopus.sqlite_store(os.path.join(SPIDER_STORE_DIR, "unsplash.db"))
        sites = [
            pyoctopus.site("unsplash.com", proxy=PROXY, limiter=pyoctopus.limiter(2)),
        ]

        processors = [(pyoctopus.ALL, pyoctopus.extractor(UnsplashPageListResponse, collector=self.collect_wallpaper))]
        octopus = pyoctopus.new(
            downloader=pyoctopus.Downloader.CURL_CFFI, processors=processors, sites=sites, store=store, threads=2
        )
        octopus.start(*seeds)

    def collect_wallpaper(self, response: UnsplashPageListResponse):
        if response.wallpapers:
            for wallpaper in response.wallpapers:
                if wallpaper.src and wallpaper.width and wallpaper.height:
                    md5 = hashlib.md5()
                    md5.update(wallpaper.src.encode("utf-8"))
                    id = md5.hexdigest()
                    meta = self.get_image_meta(wallpaper.src)
                    w = Wallpaper(
                        id=id,
                        src=wallpaper.src,
                        source="unsplash.com",
                        source_src=wallpaper.source_src,
                        description=wallpaper.description or wallpaper.alt_description,
                        author=wallpaper.author,
                        author_url=wallpaper.author_url,
                        tags=[],
                        width=wallpaper.width,
                        height=wallpaper.height,
                        ratio=round(wallpaper.width / wallpaper.height, 2),
                        size=meta.size,
                        sfw=True,
                        type=meta.type,
                        created_at=datetime.now(),
                        extra_info={},
                        colors=wallpaper.colors,
                        category=None,
                        file_id=None,
                    )
                    self.repository.insert_wallpaper(w)


if __name__ == "__main__":
    setup_logging()
    """执行任务并等待指定时间后再次执行"""
    DELAY_HOURS = 12
    logger = logging.getLogger(__name__)
    while True:
        try:
            # 执行爬虫任务
            repository = SqliteRepository(REPOSITORY_SQLITE_DB)
            spider = UnsplashSpider(repository)
            spider.run()
            # 任务执行完成后，等待12小时
            logger.info(f"任务完成，等待{DELAY_HOURS}小时后重新执行...")

        except KeyboardInterrupt:
            logger.info("程序被手动终止")
            break
        except Exception as e:
            logger.error(f"发生错误: {e}", exc_info=True)
        finally:
            time.sleep(DELAY_HOURS * 3600)
