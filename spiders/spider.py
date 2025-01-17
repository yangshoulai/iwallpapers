import abc
from common.repository import WallpaperRepository


class Spider(abc.ABC):
    def __init__(self, repository: WallpaperRepository):
        self.repository = repository

    @abc.abstractmethod
    def run(self):
        pass
