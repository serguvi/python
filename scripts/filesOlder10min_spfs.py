import os
import time
import sys
import linecache
from tutils import customlogger


def get_exception():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    file_name = f.f_code.co_filename
    linecache.checkcache(file_name)
    line = linecache.getline(file_name, lineno, f.f_globals)
    return 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(file_name, lineno, line.strip(), exc_obj)


errors = []

count = 'n/a'
dictTime = {}

script_location = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
tmp_dir = script_location + "tmp" + os.path.sep
script_name = str(__file__)

log = customlogger.customlogger(logname=script_name, filename=script_name.split("\\")[-1] + ".log",
                                logpath=tmp_dir,
                                level="INFO", maxBytes=4000000, backupCount=10)

log.info("Starting...")
log.info(sys.argv)

log.info("Директория: \\\\dbcftw\\ibs\\trc\\spfs")
list_name = None
try:
    list_name = os.listdir("\\\\dbcftw\\ibs\\trc\\spfs")
    log.info("Кол-во файлов:", len(list_name))
except Exception:
    e = get_exception()
    log.error(e)
    errors.append(e)

if list_name is not None:
    count = 0
    for filename in list_name:
        try:
            dictTime[filename] = os.path.getctime("\\\\dbcftw\\ibs\\trc\\spfs" + "\\" + filename)
            if dictTime[filename] < (time.time() - 600):
                count += 1
        except Exception:
            e = get_exception()
            log.error(e)
            errors.append(e)

    log.info("Кол-во файлов старше 10 минут:", count)

if len(errors) == 0:
    print("error 0")
else:
    print("errors:", str(errors))

print("count:", count)

log.info("Finish.")
