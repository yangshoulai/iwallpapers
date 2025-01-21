from datetime import datetime
import hashlib
import logging
import os
import time
from common.config import POSTGRES_DSN, REPOSITORY_SQLITE_DB, WALLHAVEN_API_KEY, SPIDER_STORE_DIR, PROXY
from common.log import setup_logging
from common.model import Wallpaper
from common.repository import PostgresRepository, SqliteRepository, WallpaperRepository
from spiders.spider import Spider

import pyoctopus

WALLHAVEN_API_QUERIES = {
    "apikey": WALLHAVEN_API_KEY,
    "q": "",
    "purity": "111",
    "atleast": "1920x1080",
    "page": "1",
}


class WallpaperDetailsResponse:
    id = pyoctopus.json("$.data.id")
    url = pyoctopus.json("$.data.url")
    short_url = pyoctopus.json("$.data.short_url")
    ratio = pyoctopus.json("$.data.ratio", converter=pyoctopus.float_converter())
    category = pyoctopus.json("$.data.category")
    purity = pyoctopus.json("$.data.purity")
    width = pyoctopus.json("$.data.dimension_x", converter=pyoctopus.int_converter())
    height = pyoctopus.json("$.data.dimension_y", converter=pyoctopus.int_converter())
    file_size = pyoctopus.json("$.data.file_size", converter=pyoctopus.int_converter())
    file_type = pyoctopus.json("$.data.file_type")
    created_at = pyoctopus.json("$.data.created_at")
    src = pyoctopus.json("$.data.path")
    colors = pyoctopus.json("$.data.colors[*]", multi=True)
    tags = pyoctopus.json("$.data.tags[*].name", multi=True)
    uploader = pyoctopus.json("$.data.uploader.username")

    large_url = pyoctopus.json("$.data.thumbs.large")
    original_url = pyoctopus.json("$.data.thumbs.original")
    small_url = pyoctopus.json("$.data.thumbs.small")


@pyoctopus.hyperlink(
    pyoctopus.link(
        pyoctopus.json(
            "$.data[*].id", multi=True, format_str="https://wallhaven.cc/api/v1/w/{}?apikey=" + WALLHAVEN_API_KEY
        ),
        repeatable=False,
        priority=0,
    ),
)
class WallpaperSearchResponse:
    current_page = pyoctopus.json("$.meta.current_page", converter=pyoctopus.int_converter(1))
    last_page = pyoctopus.json("$.meta.last_page", converter=pyoctopus.int_converter(1))
    total = pyoctopus.json("$.meta.total", converter=pyoctopus.int_converter(1))


class WallhavenSpider(Spider):

    def __init__(self, repository: WallpaperRepository):
        super().__init__(repository)

    def run(self):
        seed = pyoctopus.request(
            "https://wallhaven.cc/api/v1/search", queries={**WALLHAVEN_API_QUERIES, "page": ["1"]}, priority=1
        )
        store = pyoctopus.sqlite_store(os.path.join(SPIDER_STORE_DIR, "wallhaven.db"))
        sites = [
            pyoctopus.site("wallhaven.cc", proxy=PROXY, limiter=pyoctopus.limiter(2)),
        ]

        processors = [
            (pyoctopus.url_matcher(r".*/api/v1/search"), self.process_search_response),
            (
                pyoctopus.url_matcher(r".*/w/.*"),
                pyoctopus.extractor(WallpaperDetailsResponse, collector=self.collect_wallpaper),
            ),
        ]

        octopus = pyoctopus.new(processors=processors, sites=sites, store=store, threads=2)
        octopus.start(seed)

    def process_search_response(self, response: pyoctopus.Response):
        requests = []

        def _collect(w: WallpaperSearchResponse):

            if w.last_page > w.current_page and w.current_page < 500:
                requests.append(
                    pyoctopus.request(
                        f"https://wallhaven.cc/api/v1/search",
                        priority=1,
                        queries={**WALLHAVEN_API_QUERIES, "page": w.current_page + 1},
                    )
                )

        wallpapers = pyoctopus.extractor(WallpaperSearchResponse, _collect)(response)
        requests.extend(wallpapers)
        return requests

    def collect_wallpaper(self, resp: WallpaperDetailsResponse):
        try:
            if resp.width and resp.height and resp.file_size and resp.file_type and resp.src:
                md5 = hashlib.md5()
                md5.update(resp.src.encode("utf-8"))
                id = md5.hexdigest()
                wallpaper = Wallpaper(
                    id=id,
                    src=resp.src,
                    source="wallhaven.cc",
                    source_src=resp.url,
                    width=resp.width,
                    height=resp.height,
                    size=resp.file_size,
                    type=resp.file_type,
                    author=resp.uploader,
                    author_url=f"https://wallhaven.cc/user/{resp.uploader}",
                    tags=resp.tags,
                    colors=resp.colors,
                    sfw=resp.purity != "nsfw",
                    category=resp.category,
                    ratio=resp.ratio,
                    extra_info={
                        "thumbs": {
                            "large": resp.large_url,
                            "original": resp.original_url,
                            "small": resp.small_url,
                        }
                    },
                    description=None,
                    created_at=datetime.now(),
                    file_id=None,
                )
                self.repository.insert_wallpaper(wallpaper)
        except Exception as e:
            logging.error(f"Failed to insert wallpaper: {e}")


if __name__ == "__main__":
    setup_logging()
    """执行任务并等待指定时间后再次执行"""
    DELAY_HOURS = 12
    logger = logging.getLogger(__name__)

    while True:
        try:
            # 执行爬虫任务
            repository = PostgresRepository(POSTGRES_DSN)
            spider = WallhavenSpider(repository)
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
