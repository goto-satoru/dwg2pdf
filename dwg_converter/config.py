import logging
import time
from dataclasses import dataclass, field
from cognite.extractorutils.configtools import BaseConfig, LoggingConfig, StateStoreConfig
from logging.handlers import TimedRotatingFileHandler


@dataclass
class MyLoggingConfig(LoggingConfig):
    """
    Custom Logging settings, timestamp in JST
    """

    def setup_logging(self, suppress_console=False) -> None:
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)-5s] %(threadName)s - %(message)s",
            "%Y-%m-%d %H:%M:%S %z",
        )
        fmt.converter = time.localtime
        root = logging.getLogger()

        if self.console and not suppress_console and not root.hasHandlers():
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.console.level)
            console_handler.setFormatter(fmt)

            root.addHandler(console_handler)

            if root.getEffectiveLevel() > console_handler.level:
                root.setLevel(console_handler.level)

        if self.file:
            file_handler = TimedRotatingFileHandler(
                filename=self.file.path,
                when="midnight",
                utc=False,
                backupCount=self.file.retention,
                encoding='utf-8'
            )
            file_handler.setLevel(self.file.level)
            file_handler.setFormatter(fmt)

            for handler in root.handlers:
                if hasattr(handler, "baseFilename") and handler.baseFilename == file_handler.baseFilename:
                    return

            root.addHandler(file_handler)

            if root.getEffectiveLevel() > file_handler.level:
                root.setLevel(file_handler.level)


@dataclass
class Config:
    upload_queue_size: int = 50000
    parallelism: int = 10


# custom config
@dataclass
class DwgConfig:
    dwg2pdf_args: list[str]
    tmp_dir: str
    raw_db: str
    raw_table: str


@dataclass
class Config(BaseConfig):
    # custom config
    dwg: DwgConfig = field(default_factory=DwgConfig)
    # folders: list[FolderConfig] = field(default_factory=list)

    logger: MyLoggingConfig = field(default_factory=MyLoggingConfig)
    extractor: Config = field(default_factory=Config)
    state_store: StateStoreConfig = field(default_factory=StateStoreConfig)
