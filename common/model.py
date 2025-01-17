from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ChatType(Enum):
    """聊天类型"""
    PRIVATE = "private"  # 私聊
    GROUP = "group"      # 群组
    SUPERGROUP = "supergroup"  # 超级群组
    CHANNEL = "channel"  # 频道


@dataclass
class Subscription:
    """订阅信息"""
    # 聊天ID
    chat_id: int
    # 聊天类型
    chat_type: ChatType
    # 聊天标题/用户名称
    title: str
    # 用户名
    username: str | None
    # 是否为管理员
    is_admin: bool
    # 创建时间
    created_at: datetime
    # 更新时间
    updated_at: datetime
    # 订阅状态
    active: bool
    # 额外信息
    extra_info: dict


@dataclass
class Wallpaper:
    # 壁纸id
    id: str
    # 壁纸链接
    src: str
    # 壁纸来源
    source: str
    # 壁纸来源链接
    source_src: str
    # 壁纸描述
    description: str
    # 壁纸作者
    author: str
    # 壁纸作者链接
    author_url: str
    # 壁纸标签
    tags: list[str]
    # 壁纸颜色
    colors: list[str]
    # 壁纸分类
    category: str
    # 壁纸宽度
    width: int
    # 壁纸高度
    height: int
    # 壁纸宽高比
    ratio: float
    # 壁纸大小
    size: int
    # 壁纸是否为SFW
    sfw: bool
    # 壁纸类型
    type: str
    # 额外信息
    extra_info: dict
    # 壁纸创建时间
    created_at: datetime
    # Telegram file_id
    file_id: str
