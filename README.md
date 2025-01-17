# 爱壁纸机器人

一个 Telegram 壁纸机器人，支持订阅和自动推送精美壁纸。

## 功能特点

- 支持随机获取壁纸
- 支持 SFW/NSFW 内容过滤
- 支持频道/群组订阅
- 自动定时推送壁纸
- 支持多个壁纸源

## 安装部署

### 环境要求

- Python 3.10+
- SQLite 3
- 代理服务器（可选）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置文件

复制配置文件模板并修改：

```bash
cp config.example.py config.py
```

修改 `config.py` 中的配置项：

```python
# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "your_bot_token"

# 代理设置（可选）
PROXY = "socks5://127.0.0.1:1080"

# 数据库设置
REPOSITORY_SQLITE_DB = "wallpapers.db"

# Wallhaven API 设置
WALLHAVEN_API_KEY = "your_api_key"
```

### 运行

```bash
# 运行爬虫
python -m spiders.main

# 运行机器人
python -m bot.main
```

## 使用方法

### 机器人命令

- `/start` - 显示欢迎信息
- `/sfw` - 获取一张安全壁纸
- `/nsfw` - 获取一张非安全壁纸
- `/subscribe` - 订阅壁纸推送
- `/unsubscribe` - 取消订阅

### 频道/群组使用

1. 将机器人添加到频道/群组
2. 设置机器人为管理员
3. 发送 `/subscribe` 开启订阅
4. 发送 `/unsubscribe` 取消订阅

## 项目结构

```
wallpaper-bot/
├── bot/                # 机器人相关代码
│   ├── __init__.py
│   ├── main.py        # 机器人入口
│   └── telegram_bot.py # 机器人核心实现
├── common/            # 公共模块
│   ├── __init__.py
│   ├── config.py     # 配置文件
│   ├── model.py      # 数据模型
│   └── repository.py # 数据仓库
├── spiders/          # 爬虫模块
│   ├── __init__.py
│   ├── main.py      # 爬虫入口
│   └── spider.py    # 爬虫实现
├── requirements.txt  # 项目依赖
└── README.md        # 项目说明
```

## 开发计划

- [ ] 支持更多壁纸源
- [ ] 添加壁纸评分功能
- [ ] 支持按标签筛选
- [ ] 优化推送策略
- [ ] 添加管理员功能

## 贡献指南

欢迎提交 Issue 和 Pull Request。

## 许可证

本项目采用 MIT 许可证。
