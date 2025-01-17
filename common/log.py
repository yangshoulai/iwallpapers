import logging


def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logging.getLogger("pyoctopus").setLevel(logging.INFO)
    logging.getLogger("telegram").setLevel(logging.INFO)
