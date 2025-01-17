from telegram import Update, Chat, ChatMember
from telegram.ext import Application, CommandHandler, ContextTypes, ChatMemberHandler
from common.config import REPOSITORY_SQLITE_DB, TELEGRAM_BOT_TOKEN, PROXY
from common.log import setup_logging
from common.model import Subscription, ChatType, Wallpaper
from datetime import datetime
import logging
import sys
import asyncio
from typing import Set
import random
from datetime import datetime, timedelta

from common.repository import SqliteRepository, WallpaperRepository

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, repository: WallpaperRepository):
        """初始化机器人

        Args:
            repository: 数据仓库实例
        """
        self.application = None
        self.repository: WallpaperRepository = repository
        self._task: asyncio.Task | None = None
        self._last_run_time: datetime | None = None
        self._running_jobs: Set[int] = set()  # 记录正在运行的任务chat_id

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        welcome_message = (
            "👋 欢迎使用爱壁纸机器人！\n\n"
            "可用命令：\n"
            "/sfw - 随机安全壁纸\n"
            "/nsfw - 随机非安全壁纸\n"
            "/subscribe - 订阅\n"
            "/unsubscribe - 取消订阅"
        )
        await update.message.reply_text(welcome_message)

    async def sfw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /sfw 命令"""
        try:
            await self._send_wallpaper_to_chat(update.message.chat_id, sfw=True)
        except Exception as e:
            await update.message.reply_text(f"❌ 发送壁纸失败")

    async def nsfw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /nsfw 命令"""
        try:
            await self._send_wallpaper_to_chat(update.message.chat_id, sfw=False)
        except Exception as e:
            await update.message.reply_text(f"❌ 发送壁纸失败")

    async def subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /subscribe 命令"""
        chat = update.effective_chat
        if not chat:
            return

        # 创建订阅信息
        subscription = Subscription(
            chat_id=chat.id,
            chat_type=ChatType(chat.type),
            title=chat.title or chat.full_name,
            username=chat.username,
            is_admin=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            active=True,
            extra_info={},
        )

        # 保存订阅
        if self.repository.add_subscription(subscription):
            await update.message.reply_text("✅ 成功订阅，每隔一段时间会为您推送一张随机精美壁纸。")
        else:
            await update.message.reply_text("❌ 订阅失败，请稍后重试。")

    async def unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /unsubscribe 命令"""
        chat = update.effective_chat
        if not chat:
            return

        if self.repository.deactivate_subscription(chat.id):
            await update.message.reply_text("✅ 已取消订阅。")
        else:
            await update.message.reply_text("❌ 取消订阅失败，请稍后重试。")

    async def handle_chat_member_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理成员更新事件"""
        if not update.my_chat_member:
            return

        chat = update.effective_chat
        if not chat:
            return

        chat_type = ChatType(chat.type)
        if chat_type not in [ChatType.CHANNEL]:
            return

        # 检查机器人的新状态
        new_status = update.my_chat_member.new_chat_member

        # 如果是新加入或权限变更
        if new_status.status in ["administrator", "member"]:
            is_admin = new_status.status == "administrator"
            subscription = Subscription(
                chat_id=chat.id,
                chat_type=chat_type,
                title=chat.title or chat.full_name,
                username=chat.username,
                is_admin=is_admin,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                active=new_status.can_post_messages,
                extra_info={},
            )
            self.repository.add_subscription(subscription)

        # 如果被移除或失去权限
        elif new_status.status in ["left", "kicked"]:
            self.repository.deactivate_subscription(chat.id)

    async def test_bot(self) -> bool:
        """测试机器人配置是否正确"""
        try:
            me = await self.application.bot.get_me()
            logger.info("机器人信息: %s", me.to_dict())
            logger.info("机器人工作正常!")
            return True
        except Exception as e:
            logger.error("机器人检测异常: %s", e)
            return False

    def _escape_markdown(self, text: str) -> str:
        """转义 Markdown 特殊字符"""
        escape_chars = r"_*[]()~`>#+-=|{}.!"
        return "".join(f"\\{c}" if c in escape_chars else c for c in str(text))

    def _format_file_size(self, size_in_bytes: int) -> str:
        """格式化文件大小

        Args:
            size_in_bytes: 文件大小（字节）
        """
        if size_in_bytes >= 1024 * 1024:  # >= 1MB
            return f"{size_in_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_in_bytes / 1024:.0f} KB"

    def _is_valid_tag(self, tag: str) -> bool:
        """检查标签是否有效（只包含英文、数字、-、_）

        Args:
            tag: 标签
        """
        return all(c.isalnum() or c in "-_" for c in tag)

    async def _format_caption(self, wallpaper: Wallpaper) -> str:
        """格式化壁纸描述信息

        Args:
            wallpaper: 壁纸对象
        """
        resolution = self._escape_markdown(f"{wallpaper.width} × {wallpaper.height}")
        file_size = self._escape_markdown(self._format_file_size(wallpaper.size))

        # 过滤并转义标签
        valid_tags = [tag for tag in wallpaper.tags if self._is_valid_tag(tag.replace(" ", "_").replace("-", "_"))]
        tags = (
            " ".join([f"\\#{self._escape_markdown(tag.replace(' ', '_').replace('-', '_'))}" for tag in valid_tags])
            if valid_tags
            else "无标签"
        )

        source_link = f"[{self._escape_markdown(wallpaper.source)}]({self._escape_markdown(wallpaper.source_src)})"
        author_link = f"[{self._escape_markdown(wallpaper.author)}]({self._escape_markdown(wallpaper.author_url)})"

        caption = (
            f"📸 *精选壁纸* _{wallpaper.description}_\n\n"
            f"🔗 _来源_：{source_link}\n"
            f"👨‍🎨 _作者_：{author_link}\n"
            f"📏 _分辨率_：`{resolution}`\n"
            f"💾 _大小_：`{file_size}`\n"
            f"🏷️ _标签_：{tags}"
        )
        return caption

    async def _send_wallpaper_to_chat(self, chat_id: int, sfw: bool | None = None, retry: int = 3) -> bool:
        """向指定聊天发送随机壁纸

        Args:
            chat_id: 聊天ID
            retry: 重试次数

        Returns:
            bool: 是否发送成功
        """
        if chat_id in self._running_jobs:
            logger.warning("Chat %s 的发送任务正在运行中，跳过", chat_id)
            return False

        self._running_jobs.add(chat_id)
        try:
            # 获取一张随机壁纸
            wallpapers = self.repository.get_random_wallpapers(
                max_count=1,
                max_size=5 * 1024 * 1024,  # 5MB
                max_width=10000,
                max_height=10000,
                sfw=sfw,
            )

            if not wallpapers:
                logger.error("没有找到合适的壁纸")
                return False

            wallpaper = wallpapers[0]

            # 构建消息文本
            caption = await self._format_caption(wallpaper)

            for attempt in range(retry):
                try:
                    # 如果有 file_id，优先使用
                    if wallpaper.file_id:
                        await self.application.bot.send_photo(
                            chat_id=chat_id,
                            photo=wallpaper.file_id,
                            caption=caption,
                            parse_mode="MarkdownV2",
                            has_spoiler=not wallpaper.sfw,
                        )
                    else:
                        # 否则使用URL发送
                        message = await self.application.bot.send_photo(
                            chat_id=chat_id,
                            photo=wallpaper.src,
                            caption=caption,
                            parse_mode="MarkdownV2",
                            has_spoiler=not wallpaper.sfw,
                        )
                        # 保存 file_id
                        if message.photo:
                            wallpaper.file_id = message.photo[-1].file_id
                            self.repository.insert_wallpaper(wallpaper)

                    logger.info("成功发送壁纸到 Chat %s", chat_id)
                    return True

                except Exception as e:
                    if attempt == retry - 1:  # 最后一次重试
                        logger.error("发送壁纸到 Chat %s 失败: %s", chat_id, e)
                        return False
                    await asyncio.sleep(1)  # 重试前等待

        except Exception as e:
            logger.error("处理 Chat %s 的发送任务时出错: %s", chat_id, e)
            return False
        finally:
            self._running_jobs.remove(chat_id)

    async def _scheduled_wallpaper_task(self):
        """定时发送壁纸任务"""
        while True:
            try:
                now = datetime.now()

                # 检查是否需要运行
                if self._last_run_time and now - self._last_run_time < timedelta(minutes=5):
                    await asyncio.sleep(10)  # 检查间隔
                    continue

                logger.info("开始执行定时发送壁纸任务")
                self._last_run_time = now

                # 获取所有活跃订阅
                subscriptions = self.repository.get_active_subscriptions()
                if not subscriptions:
                    logger.info("没有活跃的订阅")
                    continue

                # 随机打乱顺序，避免总是同一个顺序发送
                random.shuffle(subscriptions)

                # 并发发送，但限制并发数
                tasks = []
                for subscription in subscriptions:
                    # 创建发送任务
                    task = asyncio.create_task(self._send_wallpaper_to_chat(subscription.chat_id))
                    tasks.append(task)

                    if len(tasks) >= 3:  # 最多3个并发任务
                        await asyncio.gather(*tasks)
                        tasks = []

                # 等待剩余的任务完成
                if tasks:
                    await asyncio.gather(*tasks)

                logger.info("定时发送壁纸任务完成")

            except Exception as e:
                logger.error("定时任务执行出错: %s", e)

            # 等待到下一个检查点
            await asyncio.sleep(60)  # 每分钟检查一次

    async def post_init(self, app: Application) -> None:
        """初始化回调"""
        # 启动定时任务
        self._task = asyncio.create_task(self._scheduled_wallpaper_task())
        logger.info("定时发送壁纸任务已启动")

    def initialize(self):
        """初始化机器人应用"""
        try:
            # 创建 application
            self.application = (
                Application.builder()
                .token(TELEGRAM_BOT_TOKEN)
                .proxy(PROXY if PROXY else None)
                .get_updates_connection_pool_size(8)
                .get_updates_connect_timeout(15.0)
                .get_updates_read_timeout(15.0)
                .get_updates_write_timeout(15.0)
                .get_updates_pool_timeout(15.0)
                .get_updates_proxy(PROXY if PROXY else None)
                .build()
            )

            # 添加处理器
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("sfw", self.sfw))
            self.application.add_handler(CommandHandler("nsfw", self.nsfw))
            self.application.add_handler(CommandHandler("subscribe", self.subscribe))
            self.application.add_handler(CommandHandler("unsubscribe", self.unsubscribe))
            self.application.add_handler(ChatMemberHandler(self.handle_chat_member_update))

            self.application.post_init = self.post_init

            # 测试机器人配置
            if not self.test_bot():
                logger.error("机器人配置测试失败，程序退出...")
                sys.exit(1)

        except Exception as e:
            logger.error("初始化机器人失败: %s", e)
            sys.exit(1)

    def run_polling(self):
        """运行机器人轮询"""
        try:
            logger.info("开始运行机器人轮询...")
            self.application.run_polling(
                allowed_updates=[Update.MESSAGE, Update.MY_CHAT_MEMBER],
                drop_pending_updates=False,
                poll_interval=1.0,
            )
        except Exception as e:
            logger.error("运行机器人轮询失败: %s", e)

    def run(self):
        """运行机器人"""
        try:
            self.initialize()
            self.run_polling()
        except KeyboardInterrupt:
            logger.info("收到退出信号，正在关闭机器人...")
            # 取消定时任务
            if self._task:
                self._task.cancel()
            sys.exit(0)
        except Exception as e:
            logger.error("运行机器人失败: %s", e)
            # 取消定时任务
            if self._task:
                self._task.cancel()
            sys.exit(1)


if __name__ == "__main__":
    setup_logging()
    repository = SqliteRepository(REPOSITORY_SQLITE_DB)
    bot = TelegramBot(repository)
    bot.run()
