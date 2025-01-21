import abc
import logging
import requests
from typing import Dict, Optional
from urllib.parse import urlparse
from common.config import PROXY
from common.model import WallpaperMeta
from common.repository import WallpaperRepository

logger = logging.getLogger(__name__)


class Spider(abc.ABC):
    """爬虫基类"""

    # 常见图片 MIME 类型映射
    IMAGE_TYPES = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/bmp": "bmp",
    }

    # 默认请求头
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    def __init__(self, repository: WallpaperRepository):
        """初始化爬虫

        Args:
            repository: 壁纸仓库实例
        """
        self.repository = repository
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self.session.proxies = {"http": PROXY, "https": PROXY} if PROXY else {}

    @abc.abstractmethod
    def run(self):
        """运行爬虫"""
        pass

    def get_image_meta(self, src: str) -> WallpaperMeta:
        """获取图片元数据

        Args:
            src: 图片URL
            timeout: 请求超时时间（秒）
            max_size: 最大下载大小（字节）

        Returns:
            Dict: 图片元数据，包含以下字段：
                - size: 文件大小（字节）
                - type: 文件类型（MIME类型）
                - ext: 文件扩展名
                - width: 图片宽度（如果可用）
                - height: 图片高度（如果可用）
        """
        meta = WallpaperMeta(
            size=0,
            type=None,
            ext=None,
            width=0,
            height=0,
        )
        try:
            # 发送 HEAD 请求获取基本信息
            head_resp = self.session.head(src, timeout=5, allow_redirects=True)
            head_resp.raise_for_status()

            # 获取文件大小
            size = int(head_resp.headers.get("content-length", 0))
            meta.size = size
            # 获取文件类型
            content_type = head_resp.headers.get("content-type", "").lower()
            meta.type = content_type
        except Exception as e:
            logging.error(f"Failed to get image meta: {e}")

        return meta
