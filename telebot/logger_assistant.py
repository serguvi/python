import sys
import linecache
import os
import logging
import traceback
import time
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


def get_exception() -> str:
    """
    Returns a string with info about Exception to be written at log.
    """
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    line_number = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, line_number, f.f_globals)
    return f'EXCEPTION IN ({filename}, LINE {line_number} "{line.strip()}"): {exc_obj}, {[traceback.format_exc()]}'


def get_script_location() -> Path:
    """
    Returns location of script.
    """
    return Path(sys.argv[0]).parent


def get_script_name() -> str:
    """
    Returns name of script.
    """
    return Path(sys.argv[0]).name


def make_and_get_screenshot_location(script_location: Path) -> Path:
    """
    Make screenshot directory in current directory

    :return: Path to the created directory
    """
    screenshot_location = script_location / 'png'
    if not os.path.exists(screenshot_location):
        os.mkdir(screenshot_location)
    return screenshot_location


def make_and_get_logs_path() -> Path:
    """
    Make logs directory in current directory

    :return: Path to the created directory
    """
    logs_path = get_script_location() / "logs"
    if not os.path.exists(logs_path):
        os.mkdir(logs_path)
    return logs_path


def get_logger(filename: str, log_path: Path):
    """
    Make logger

    :return: logger
    """
    logger = logging.getLogger(filename)

    logger.setLevel(logging.INFO)
    file_handler = RotatingFileHandler(str(log_path / f"{filename}.log"), maxBytes=4000000, backupCount=10)
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(name)s %(levelname)s [%(filename)s] %(lineno)s %(msg)s',
                                  datefmt="%Y-%m-%dT%H:%M:%S")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def png_remover(script_location: Path, script_name, logger):
    """
    Remove old .png files from png_path
    """
    png_path = script_location / 'png'
    png_list = []
    t = time.time()
    max_age = 60 * 60 * 24
    try:
        for fname in os.listdir(png_path):
            if (script_name.lower() in fname.lower()) and (".png" in fname.lower()):
                fdate = os.stat(png_path / fname).st_mtime
                if (t - fdate) > max_age:
                    png_list.append(png_path / fname)
    except Exception as e:
        logger.error(e)

    for fpath in png_list:
        try:
            os.unlink(fpath)
        except Exception as e:
            logger.error(e)


def logs_remover(script_location: Path, logger):
    """
    Remove old .log.\d+ files from logs_path_path
    """
    logs_path = script_location / 'logs'
    delete_logs_list = []
    files = os.listdir(logs_path)
    try:
        for file in files:
            search = re.search(r".*\.log\.(\d+)", file)
            if search:
                number = int(search.group(1))
                if number > 10:
                    delete_logs_list.append(logs_path / file)
    except Exception as e:
        logger.error(get_exception())
        return
    for file in delete_logs_list:
        try:
            os.unlink(file)
        except Exception as e:
            logger.error(get_exception())
            return
