import atexit
from pathlib import Path
from loguru import logger
import time
import threading
import tempfile


class TempManager:
    def __init__(self, check_interval=60, remove_timeout=600):
        self.check_interval = check_interval
        self.remove_timeout = remove_timeout
        self.timer = None
        self.temp_dir = None
        atexit.register(self.exit)

    def enter(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="py_temp_manager-"))
        logger.info(f"Temporary directory created at {self.temp_dir}")
        self.start_periodic_check()

    def exit(self):
        if self.timer:
            self.stop_periodic_check()
        if self.temp_dir:
            self.remove_temp_dir()

    def __enter__(self):
        self.enter()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.exit()

    def start_periodic_check(self):
        self.timer = threading.Timer(self.check_interval, self.remove_old_files)
        self.timer.start()

    def stop_periodic_check(self):
        self.timer.cancel()
        self.timer = None

    def remove_old_files(self):
        for file_path in self.temp_dir.iterdir():
            if time.time() - file_path.stat().st_mtime > self.remove_timeout:
                file_path.unlink()
                logger.info(f"Removed old file: {file_path}")
        self.start_periodic_check()

    def remove_temp_dir(self):
        for file_path in self.temp_dir.iterdir():
            file_path.unlink()
            logger.debug(f"Removed file: {file_path}")
        self.temp_dir.rmdir()
        logger.info(f"Temporary directory {self.temp_dir} deleted")
        self.temp_dir = None

    def request_temp_file(self, prefix: str = None, suffix: str = None):
        temp_file = tempfile.NamedTemporaryFile(
            dir=self.temp_dir, prefix=prefix, suffix=suffix, delete=False
        ).name
        return temp_file
