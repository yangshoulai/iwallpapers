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

HEADERS = {"Cookie": ""}


class WallpaperDetailsResponse:
    url = pyoctopus.url()
    src = pyoctopus.css(".hub-photomodal > a", attr="href")
    width = pyoctopus.regex(
        r"(\d+)x.*",
        1,
        pyoctopus.xpath("//ul[@class='photobaseinfo clearfix']/li[1]/span[1]/text()"),
        converter=pyoctopus.int_converter(),
    )
    height = pyoctopus.regex(
        r".*x(\d+)",
        1,
        pyoctopus.xpath("//ul[@class='photobaseinfo clearfix']/li[1]/span[1]/text()"),
        converter=pyoctopus.int_converter(),
    )
    tags = pyoctopus.xpath("//ul[@class='hub-tags clearfix']/li/a/text()", multi=True)

    author = pyoctopus.regex(r"(.*) / .*", 1, pyoctopus.xpath('//p/a[@class="profile-link"]/text()'))
    author_url = pyoctopus.xpath('//p/a[@class="profile-link"]/@href', format_str="https://wallhere.com{}")

    sketchy = pyoctopus.attr("sketchy", converter=pyoctopus.bool_converter())


@pyoctopus.hyperlink(
    pyoctopus.link(pyoctopus.regex(r'<a href="(.*?)"', 1), repeatable=False, priority=2, attr_props=["sketchy"]),
)
class WallpaperItem:
    sketchy = pyoctopus.xpath(
        '//div[contains(concat(" ", @class, " "), " item-sketchy ")]/@class',
        converter=pyoctopus.bool_converter(["item item-sketchy"], False),
    )


@pyoctopus.hyperlink(
    pyoctopus.link(
        pyoctopus.xpath("//a[@class='hub-itemmore']/@data-score", pyoctopus.json("$.data")),
        priority=1,
    )
)
class WallpaperSearchResponse:
    wallpapers = pyoctopus.embedded(
        pyoctopus.xpath("//div[contains(concat(' ', @class, ' '), ' item ')]", pyoctopus.json("$.data"), multi=True),
        WallpaperItem,
    )


class WallhereSpider(Spider):

    def __init__(self, repository: WallpaperRepository):
        super().__init__(repository)

    def run(self):
        seed = pyoctopus.request(
            "https://wallhere.com/zh/wallpapers?order=latest&NSFW=on&page=1&format=json", queries={}, priority=1
        )
        store = pyoctopus.sqlite_store(os.path.join(SPIDER_STORE_DIR, "wallhere.db"))
        sites = [
            pyoctopus.site("wallhere.com", proxy=PROXY, limiter=pyoctopus.limiter(3)),
        ]

        processors = [
            (pyoctopus.JSON, pyoctopus.extractor(WallpaperSearchResponse)),
            (
                pyoctopus.HTML,
                pyoctopus.extractor(WallpaperDetailsResponse, collector=self.collect_wallpaper),
            ),
        ]

        octopus = pyoctopus.new(
            processors=processors, sites=sites, store=store, threads=2, ignore_seed_when_has_waiting_requests=True
        )
        octopus.start(seed)

    def collect_wallpaper(self, resp: WallpaperDetailsResponse):
        try:
            if resp.width and resp.height and resp.src:
                meta = self.get_image_meta(resp.src)
                if meta.size and meta.type:
                    md5 = hashlib.md5()
                    md5.update(resp.src.encode("utf-8"))
                    id = md5.hexdigest()
                    wallpaper = Wallpaper(
                        id=id,
                        src=resp.src,
                        source="wallhere.com",
                        source_src=resp.url,
                        width=resp.width,
                        height=resp.height,
                        size=meta.size,
                        type=meta.type,
                        author=resp.author,
                        author_url=resp.author_url,
                        tags=resp.tags,
                        colors=[],
                        sfw=not resp.sketchy,
                        category=None,
                        ratio=round(resp.width / resp.height, 2),
                        extra_info={},
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
            spider = WallhereSpider(repository)
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
