"""Base class for handling standard things like cache files and logs
"""
import os
import sys
import time
import pickle
import smtplib
import typing as t
from datetime import datetime
from abc import ABCMeta
from filelock import FileLock

os.environ['TZ'] = 'UTC'
time.tzset()

class CacheNameError(Exception):
    """Invalid cache name"""

class BaseBot(metaclass=ABCMeta):
    """The base class for exchanges and trading bots

    See CONFIG_DEFAULTS for more information on attributes that are set during _configure().

    Args:
        config_path (str): The path to the configuration file

    Attributes:
        config (configparser.ConfigParser): ConfigParse object from config_path
    """
    # pylint: disable=attribute-defined-outside-init
    # pylint: disable=too-few-public-methods
    # pylint: disable=no-self-use
    # pylint: disable=bare-except
    # pylint: disable=no-member
    def __init__(self, config) -> None:
        self.config = config


    def init_cache(self) -> None:
        """Verify cache_file name and load existing cache if it exists"""
        self.cache = {}
        if not self.cache_file.endswith('.cache'):
            raise CacheNameError('ERROR: Cache filenames must end in .cache')
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "rb") as cache_fd:
                self.cache = pickle.load(cache_fd)

    def init_lock(self) -> None:
        """Initialize and open lockfile.

        Note that this is done to avoid running duplicate configurations at the same time.
        """
        self.lock_file = self.cache_file.replace('.cache', '.lock')
        self.lock = FileLock(self.lock_file, timeout=1)
        try:
            self.lock.acquire()
        except:
            print('ERROR: Failed to acquire lock: {}'.format(self.lock_file))
            print('Is another process already running with this config?')
            sys.exit(1)

    def write_cache(self) -> None:
        """Write self.cache to disk atomically"""
        with open(self.cache_file + '-tmp', "wb") as cache_fd:
            pickle.dump(self.cache, cache_fd)
            os.fsync(cache_fd)
        if os.path.exists(self.cache_file):
            os.rename(self.cache_file, self.cache_file + '-prev')
        os.rename(self.cache_file + '-tmp', self.cache_file)

    def _log(self, path: t.AnyStr, msg: t.Any, custom_datetime=None) -> None:
        """TODO: Replace me with Python logging"""
        if custom_datetime:
            now = custom_datetime
        else:
            now = datetime.now()
        print('{} {}'.format(now, str(msg).strip()))
        if not self.log_disabled:
            with open(path, 'a') as log_fd:
                log_fd.write('{} {}\n'.format(now, str(msg).strip()))

    def logit(self, msg: t.Any, custom_datetime=None) -> None:
        """TODO: Replace me with Python logging"""
        if not self.coin in msg:
            msg = '{} {}'.format(self.coin, msg)
        self._log(self.log_file, msg, custom_datetime=custom_datetime)

    def send_email(self, subject: str, msg: t.Optional[t.AnyStr] = None) -> None:
        """TODO: Add auth, currently setup to relay locally or relay-by-IP"""
        for email in self.mail_to:
            if not email.strip():
                continue
            headers = "From: %s\r\nTo: %s\r\nSubject: %s %s\r\n\r\n" % (
                self.mail_from, email, self.coin, subject)
            if not msg:
                msg2 = subject
            else:
                msg2 = msg
            msg2 = headers + msg2
            server = smtplib.SMTP(self.mail_host)
            server.sendmail(self.mail_from, email, msg2)
            server.quit()
            time.sleep(0.1)
