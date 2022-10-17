import os
import sys
import linecache
from tutils import customlogger
from urllib.request import Request, urlopen, ssl, socket
from urllib.error import URLError, HTTPError
import json
import re
import datetime


class Date:
    def __init__(self, string):
        self.day = int(re.search(r'\w+ (\d+) \d+:\d+:\d+ \d+', string).group(1))
        self.year = int(re.search(r'\w+ \d+ \d+:\d+:\d+ (\d+)', string).group(1))
        self.hour = int(re.search(r'\w+ \d+ (\d+):\d+:\d+ \d+', string).group(1))
        self.minute = int(re.search(r'\w+ \d+ \d+:(\d+):\d+ \d+', string).group(1))
        self.second = int(re.search(r'\w+ \d+ \d+:\d+:(\d+) \d+', string).group(1))
        month = re.search(r'(\w)+ \d+ \d+:\d+:\d+ \d+', string).group(1)
        if month in 'Jan':
            self.month = 1
        elif month in 'Feb':
            self.month = 2
        elif month in 'Mar':
            self.month = 3
        elif month in 'Apr':
            self.month = 4
        elif month in 'May':
            self.month = 5
        elif month in 'Jun':
            self.month = 6
        elif month in 'Jul':
            self.month = 7
        elif month in 'Aug':
            self.month = 8
        elif month in 'Sept':
            self.month = 9
        elif month in 'Oct':
            self.month = 10
        elif month in 'Nov':
            self.month = 11
        elif month in 'Dec':
            self.month = 12


def get_exception():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    return 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)


script_location = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
tmp_dir = script_location + "tmp" + os.path.sep
script_name = str(__file__)

log = customlogger.customlogger(logname=script_name, filename=script_name.split("\\")[-1] + ".log",
                                logpath=tmp_dir,
                                level="INFO", maxBytes=4000000, backupCount=10)

log.info("")
log.info("Starting...")
log.info(sys.argv)

url = '...'
port = '5000'

hostname = url
context = ssl.create_default_context()

try:
    with socket.create_connection((hostname, port)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            log.info(ssock.version())
            data = json.dumps(ssock.getpeercert())
    log.info(data)
    termCert = re.search(r'\"notAfter\": \"(.*) GMT\"', data)
except Exception:
    e = get_exception()
    log.error(e)

if 'termCert' in globals():
    log.info('Сертификат до: ' + str(termCert.group(1)))
    certDate = Date(termCert.group(1))
    now = datetime.datetime.now()
    endOfCert = datetime.datetime(certDate.year, certDate.month, certDate.day, certDate.hour, certDate.minute,
                                  certDate.second)
    log.info('До окончания: ' + str((endOfCert - now).days) + ' дней')

log.info("Finish.")
