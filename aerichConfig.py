import os

from src.main.core.config import Config


try:
    import config

    dbUrl = config.sql
except ImportError:
    dbUrl = os.environ["ZIBOT_DB_URL"]

cfg = Config("", dbUrl, useAerich=True)
t = cfg.tortoiseConfig
