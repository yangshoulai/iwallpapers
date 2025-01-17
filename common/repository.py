import abc
from datetime import datetime
import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager
from .model import Wallpaper, Subscription, ChatType


class WallpaperRepository(abc.ABC):
    """壁纸仓库抽象基类

    定义了壁纸数据访问的基本接口，包括:
    - 插入/更新壁纸
    - 按ID查询壁纸
    - 按源地址查询壁纸
    - 随机获取壁纸

    所有实现类都必须实现这些基本方法。
    """

    @abc.abstractmethod
    def insert_wallpaper(self, wallpaper: Wallpaper) -> bool:
        """插入或更新壁纸数据

        Args:
            wallpaper: 要插入的壁纸对象

        Returns:
            bool: 操作是否成功
        """
        pass

    @abc.abstractmethod
    def get_wallpaper_by_id(self, wallpaper_id: str) -> Optional[Wallpaper]:
        """根据ID获取壁纸

        Args:
            wallpaper_id: 壁纸ID

        Returns:
            Optional[Wallpaper]: 壁纸对象，不存在时返回None
        """
        pass

    @abc.abstractmethod
    def get_wallpaper_by_src(self, src: str) -> List[Wallpaper]:
        """根据源地址获取壁纸

        Args:
            src: 壁纸源地址

        Returns:
            List[Wallpaper]: 匹配的壁纸列表
        """
        pass

    @abc.abstractmethod
    def get_random_wallpapers(
        self, max_count: int, max_size: int, max_width: int, max_height: int, sfw: bool | None
    ) -> List[Wallpaper]:
        """获取随机壁纸

        Args:
            max_count: 最大返回数量
            max_size: 最大文件大小（字节）
            max_width: 最大宽度
            max_height: 最大高度
            sfw: 是否为安全内容，None表示不限制

        Returns:
            List[Wallpaper]: 随机壁纸列表
        """
        pass


class SubscriptionRepository(abc.ABC):
    """订阅信息仓库抽象基类"""

    @abc.abstractmethod
    def add_subscription(self, subscription: Subscription) -> bool:
        """添加订阅

        Args:
            subscription: 订阅信息

        Returns:
            bool: 操作是否成功
        """
        pass

    @abc.abstractmethod
    def update_subscription(self, chat_id: int, updates: dict) -> bool:
        """更新订阅信息

        Args:
            chat_id: 聊天ID
            updates: 要更新的字段

        Returns:
            bool: 操作是否成功
        """
        pass

    @abc.abstractmethod
    def get_subscription(self, chat_id: int) -> Optional[Subscription]:
        """获取订阅信息

        Args:
            chat_id: 聊天ID

        Returns:
            Optional[Subscription]: 订阅信息
        """
        pass

    @abc.abstractmethod
    def get_active_subscriptions(self) -> List[Subscription]:
        """获取所有活跃的订阅"""
        pass

    @abc.abstractmethod
    def deactivate_subscription(self, chat_id: int) -> bool:
        """停用订阅

        Args:
            chat_id: 聊天ID

        Returns:
            bool: 操作是否成功
        """
        pass


class SqliteRepository(WallpaperRepository, SubscriptionRepository):
    def __init__(self, db_path: str = "iwallpapers.db"):
        """初始化数据库连接

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表和索引"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS wallpapers (
            id TEXT PRIMARY KEY,
            src TEXT NOT NULL,
            source TEXT NOT NULL,
            source_src TEXT,
            description TEXT,
            author TEXT,
            author_url TEXT,
            tags TEXT,  -- 以逗号分隔的标签字符串
            colors TEXT,  -- 以逗号分隔的颜色字符串
            category TEXT,
            width INTEGER,
            height INTEGER,
            ratio REAL,
            size INTEGER,
            sfw BOOLEAN,
            type TEXT,
            extra_info TEXT,  -- JSON字符串
            file_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # 创建索引的SQL语句
        create_indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_source ON wallpapers(source)",
            "CREATE INDEX IF NOT EXISTS idx_src ON wallpapers(src)",
            "CREATE INDEX IF NOT EXISTS idx_file_id ON wallpapers(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_dimensions_size ON wallpapers(width, height, size)",
        ]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 创建表
            cursor.execute(create_table_sql)
            # 创建索引
            for index_sql in create_indexes_sql:
                cursor.execute(index_sql)
            conn.commit()

        # 创建订阅表
        create_subscription_table_sql = """
        CREATE TABLE IF NOT EXISTS subscriptions (
            chat_id INTEGER PRIMARY KEY,
            chat_type TEXT NOT NULL,
            title TEXT NOT NULL,
            username TEXT,
            is_admin BOOLEAN NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            extra_info TEXT
        )
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_subscription_table_sql)
            conn.commit()

    def insert_wallpaper(self, wallpaper: Wallpaper) -> bool:
        """插入壁纸数据

        Args:
            wallpaper: Wallpaper对象

        Returns:
            bool: 插入是否成功
        """
        insert_sql = """
        INSERT OR REPLACE INTO wallpapers (
            id, src, source, source_src, description, author, author_url,
            tags, colors, category, width, height, ratio, size, sfw, type,
            extra_info, file_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    insert_sql,
                    (
                        wallpaper.id,
                        wallpaper.src,
                        wallpaper.source,
                        wallpaper.source_src,
                        wallpaper.description,
                        wallpaper.author,
                        wallpaper.author_url,
                        ",".join(wallpaper.tags),
                        ",".join(wallpaper.colors),
                        wallpaper.category,
                        wallpaper.width,
                        wallpaper.height,
                        wallpaper.ratio,
                        wallpaper.size,
                        wallpaper.sfw,
                        wallpaper.type,
                        json.dumps(wallpaper.extra_info),
                        wallpaper.file_id,
                        wallpaper.created_at,
                    ),
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error("Error inserting wallpaper: %s", e)
            return False

    def get_wallpaper_by_id(self, wallpaper_id: str) -> Optional[Wallpaper]:
        """根据ID获取壁纸

        Args:
            wallpaper_id: 壁纸ID

        Returns:
            Optional[Wallpaper]: 壁纸对象，如果不存在返回None
        """
        select_sql = "SELECT * FROM wallpapers WHERE id = ?"

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (wallpaper_id,))
                row = cursor.fetchone()

                if row:
                    # 将数据库行转换为Wallpaper对象
                    return Wallpaper(
                        id=row[0],
                        src=row[1],
                        source=row[2],
                        source_src=row[3],
                        description=row[4],
                        author=row[5],
                        author_url=row[6],
                        tags=row[7].split(",") if row[7] else [],
                        colors=row[8].split(",") if row[8] else [],
                        category=row[9],
                        width=row[10],
                        height=row[11],
                        ratio=row[12],
                        size=row[13],
                        sfw=bool(row[14]),
                        type=row[15],
                        extra_info=json.loads(row[16]) if row[16] else {},
                        file_id=row[17],
                        created_at=row[18],
                    )
                return None
        except sqlite3.Error as e:
            self.logger.error("Error getting wallpaper by id: %s", e)
            return None

    def _row_to_wallpaper(self, row) -> Optional[Wallpaper]:
        """将数据库行转换为Wallpaper对象

        Args:
            row: 数据库查询结果行

        Returns:
            Optional[Wallpaper]: 转换后的Wallpaper对象
        """
        try:
            return Wallpaper(
                id=row[0],
                src=row[1],
                source=row[2],
                source_src=row[3],
                description=row[4],
                author=row[5],
                author_url=row[6],
                tags=row[7].split(",") if row[7] else [],
                colors=row[8].split(",") if row[8] else [],
                category=row[9],
                width=row[10],
                height=row[11],
                ratio=row[12],
                size=row[13],
                sfw=bool(row[14]),
                type=row[15],
                extra_info=json.loads(row[16]) if row[16] else {},
                file_id=row[17],
                created_at=row[18],
            )
        except Exception as e:
            self.logger.error("Error converting row to wallpaper: %s", e)
            return None

    def get_wallpaper_by_src(self, src: str) -> List[Wallpaper]:
        """根据URL获取壁纸列表

        Args:
            url: 壁纸URL

        Returns:
            List[Wallpaper]: 匹配URL的壁纸列表
        """
        select_sql = "SELECT * FROM wallpapers WHERE src = ?"
        wallpapers = []

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (src,))
                rows = cursor.fetchall()

                for row in rows:
                    wallpaper = self._row_to_wallpaper(row)
                    if wallpaper:
                        wallpapers.append(wallpaper)

                return wallpapers
        except sqlite3.Error as e:
            self.logger.error("Error getting wallpapers by src: %s", e)
            return []

    def get_random_wallpapers(
        self, max_count: int, max_size: int, max_width: int, max_height: int, sfw: bool | None
    ) -> List[Wallpaper]:
        """获取随机壁纸

        Args:
            max_count: 最大返回数量
            max_size: 最大文件大小（字节）
            max_width: 最大宽度
            max_height: 最大高度
            sfw: 是否为安全内容，None表示不限制

        Returns:
            List[Wallpaper]: 随机壁纸列表
        """
        conditions = ["1=1"]  # 始终为真的条件作为基础
        params = []

        # 构建查询条件
        if max_size > 0:
            conditions.append("size <= ?")
            params.append(max_size)

        if max_width > 0:
            conditions.append("width <= ?")
            params.append(max_width)

        if max_height > 0:
            conditions.append("height <= ?")
            params.append(max_height)

        if sfw is not None:
            conditions.append("sfw = ?")
            params.append(sfw)

        # 组合SQL语句
        select_sql = f"""
        SELECT * FROM wallpapers 
        WHERE {' AND '.join(conditions)}
        ORDER BY RANDOM()
        LIMIT ?
        """
        params.append(max_count)

        wallpapers = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, params)
                rows = cursor.fetchall()

                for row in rows:
                    wallpaper = self._row_to_wallpaper(row)
                    if wallpaper:
                        wallpapers.append(wallpaper)

                return wallpapers
        except sqlite3.Error as e:
            self.logger.error("Error getting random wallpapers: %s", e)
            return []

    def add_subscription(self, subscription: Subscription) -> bool:
        """添加订阅信息"""
        sql = """
        INSERT OR REPLACE INTO subscriptions (
            chat_id, chat_type, title, username, is_admin, 
            created_at, updated_at, active, extra_info
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql,
                    (
                        subscription.chat_id,
                        subscription.chat_type.value,
                        subscription.title,
                        subscription.username,
                        subscription.is_admin,
                        subscription.created_at,
                        subscription.updated_at,
                        subscription.active,
                        json.dumps(subscription.extra_info),
                    ),
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error("Error adding subscription: %s", e)
            return False

    def update_subscription(self, chat_id: int, updates: dict) -> bool:
        """更新订阅信息"""
        if not updates:
            return True

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        sql = f"UPDATE subscriptions SET {set_clause} WHERE chat_id = ?"

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, [*updates.values(), chat_id])
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error("Error updating subscription: %s", e)
            return False

    def get_subscription(self, chat_id: int) -> Optional[Subscription]:
        """获取订阅信息"""
        sql = "SELECT * FROM subscriptions WHERE chat_id = ?"

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (chat_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_subscription(row)
                return None
        except sqlite3.Error as e:
            self.logger.error("Error getting subscription: %s", e)
            return None

    def get_active_subscriptions(self) -> List[Subscription]:
        """获取所有活跃的订阅"""
        sql = "SELECT * FROM subscriptions WHERE active = TRUE"
        subscriptions = []

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()
                for row in rows:
                    sub = self._row_to_subscription(row)
                    if sub:
                        subscriptions.append(sub)
                return subscriptions
        except sqlite3.Error as e:
            self.logger.error("Error getting active subscriptions: %s", e)
            return []

    def deactivate_subscription(self, chat_id: int) -> bool:
        """停用订阅"""
        return self.update_subscription(chat_id, {"active": False, "updated_at": datetime.now()})

    def _row_to_subscription(self, row) -> Optional[Subscription]:
        """将数据库行转换为订阅对象"""
        try:
            return Subscription(
                chat_id=row[0],
                chat_type=ChatType(row[1]),
                title=row[2],
                username=row[3],
                is_admin=bool(row[4]),
                created_at=datetime.fromisoformat(row[5]),
                updated_at=datetime.fromisoformat(row[6]),
                active=bool(row[7]),
                extra_info=json.loads(row[8]) if row[8] else {},
            )
        except Exception as e:
            self.logger.error("Error converting row to subscription: %s", e)
            return None
