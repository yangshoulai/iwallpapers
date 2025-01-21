from datetime import datetime
import hashlib
import logging
import os
import time

from common.config import PROXY, REPOSITORY_SQLITE_DB, SPIDER_STORE_DIR, CIVITAI_API_KEY, POSTGRES_DSN
from common.log import setup_logging
from common.model import Wallpaper
from common.repository import PostgresRepository, SqliteRepository, WallpaperRepository
from spiders.spider import Spider
import pyoctopus


HEADERS = {
    "Authorization": f"Bearer {CIVITAI_API_KEY}",
    "Content-Type": "application/json",
}


class CivitaiImage:
    id = pyoctopus.json("$.id", converter=pyoctopus.int_converter(0))
    src = pyoctopus.json("$.url")
    author = pyoctopus.json("$.username")
    nsfw = pyoctopus.json("$.nsfw", converter=pyoctopus.bool_converter())
    width = pyoctopus.json("$.width", converter=pyoctopus.int_converter(0))
    height = pyoctopus.json("$.height", converter=pyoctopus.int_converter(0))
    type = pyoctopus.json("$.type")
    nsfw_level = pyoctopus.json("$.nsfwLevel")
    model = pyoctopus.json("$.meta.Model")


def terminat(r: "CivitaiImageSearchResponse", content: str, resp: pyoctopus.Response) -> bool:

    return r.count and r.count >= 6000


@pyoctopus.hyperlink(
    pyoctopus.link(pyoctopus.json("$.metadata.nextPage"), headers=HEADERS, priority=1, terminable=terminat)
)
class CivitaiImageSearchResponse:
    wallpapers = pyoctopus.embedded(pyoctopus.json("$.items[*]", multi=True), CivitaiImage)

    count = pyoctopus.regex(
        r"^.*cursor=(\d+)%7C.*$",
        group=1,
        selector=pyoctopus.json("$.metadata.nextPage"),
        converter=pyoctopus.int_converter(),
    )


class CivitaiSpider(Spider):
    def __init__(self, repository: WallpaperRepository):
        super().__init__(repository)

    def run(self):
        seeds = [
            pyoctopus.request(
                f"https://civitai.com/api/v1/images?sort=Newest&period=Month&nsfw=Soft", priority=1, headers=HEADERS
            ),
            pyoctopus.request(
                f"https://civitai.com/api/v1/images?sort=Newest&period=Month&nsfw=Mature", priority=1, headers=HEADERS
            ),
        ]
        store = pyoctopus.sqlite_store(os.path.join(SPIDER_STORE_DIR, "civitai.db"))
        sites = [
            pyoctopus.site("civitai.com", proxy=PROXY, limiter=pyoctopus.limiter(4)),
        ]

        processors = [
            (pyoctopus.ALL, pyoctopus.extractor(CivitaiImageSearchResponse, collector=self.collect_wallpaper))
        ]
        octopus = pyoctopus.new(processors=processors, sites=sites, store=store, threads=2)
        octopus.start(*seeds)

    def collect_wallpaper(self, response: CivitaiImageSearchResponse):
        if response.wallpapers:
            for wallpaper in response.wallpapers:
                if wallpaper.src and wallpaper.width and wallpaper.height and wallpaper.type == "image":
                    md5 = hashlib.md5()
                    md5.update(wallpaper.src.encode("utf-8"))
                    id = md5.hexdigest()
                    meta = self.get_image_meta(wallpaper.src)
                    if meta.size and meta.type:
                        w = Wallpaper(
                            id=id,
                            src=wallpaper.src,
                            source="civitai.com",
                            source_src=f"https://civitai.com/images/{wallpaper.id}",
                            description=None,
                            author=wallpaper.author,
                            author_url=f"https://civitai.com/user/{wallpaper.author}",
                            tags=[x for x in ["ai", "artwork", wallpaper.nsfw_level] if x and x != "None"],
                            width=wallpaper.width,
                            height=wallpaper.height,
                            ratio=round(wallpaper.width / wallpaper.height, 2),
                            size=meta.size,
                            sfw=not wallpaper.nsfw,
                            type=meta.type,
                            created_at=datetime.now(),
                            extra_info={},
                            colors=[],
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
            repository = PostgresRepository(POSTGRES_DSN)
            spider = CivitaiSpider(repository)
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
