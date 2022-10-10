import os
import time
import sys
import linecache
from tutils import customlogger
from urllib.request import Request, urlopen, ssl, socket
from urllib.error import URLError, HTTPError
import json


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

log.info("Starting...")
log.info(sys.argv)

url = 'https://...'
port = '443'

hostname = url
context = ssl.create_default_context()
log.info(context)

try:
    with socket.create_connection((hostname, port)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            log.info(ssock.version())
            data = json.dumps(ssock.getpeercert())
    log.info(data)
except Exception:
    e = get_exception()
    log.error(e)

try:
    HTML = urllib.request.urlopen(url)
    log.info(HTML)
except Exception:
    e = get_exception()
    log.error(e)

try:
    r = request.get(url)
    log.info(r.peer_certificate.get_notAfter())
except Exception:
    e = get_exception()
    log.error(e)

try:
    process = os.popen('ping ...')
    preprocessed = process.read().split('\n')
    process.close()
except Exception:
    e = get_exception()
    log.error(e)

for line in preprocessed:
    if preprocessed.index(line) == 1:
        log.info(line)

log.info("Finish.")
