import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import re
import os
import sys
import linecache
from tutils import customlogger


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

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

endpoint = f"https://.../_xpack/sql?format=csv"

headers = {'Accept': 'application/json', 'Content-type': 'application/json'}

count = "n/a"
error = 0

query = ("""
{
  "query" : 
    "select count(*) from \\"...\\" where err_message like '%Необработанное исключение при обработке события%'  ",
    "filter": {
   "range": {
      "@timestamp": {
        "gte": "now-30m"
      }
    }
  }
}

""").encode('utf-8')

try:
    r = requests.get(endpoint, data=query, auth=('...', '...'), verify=False, headers=headers)
    log.info("Статус запроса: " + str(r.status_code))
except Exception:
    e = get_exception()
    log.error(e)
    error += 1

if "r" in globals():
    if r.status_code == 200:
        listRequests = r.text.split("\r\n")
        count = listRequests[1]
        log.info("Кол-во: " + str(count))
    else:
        error += 1

print("Errors:", error)
print("Count:", count)

log.info("Finish.")
