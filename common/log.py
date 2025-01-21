import logging


def setup_logging():
    """设置日志配置

    - 添加线程名到日志格式
    - 设置日志级别
    - 配置第三方库的日志级别
    """
    # 创建日志目录

    # 设置日志格式，添加线程名
    log_format = "%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s"

    # 配置基本日志
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            # 控制台输出
            logging.StreamHandler()
        ],
    )

    # 设置第三方库的日志级别
    logging.getLogger("pyoctopus").setLevel(logging.INFO)
    logging.getLogger("telegram").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
