import os, sys, linecache, time
import datetime, argparse
import vertica_python
import cx_Oracle, json
import redis
from redis.sentinel import Sentinel
from tutils import customlogger


def get_exception():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    return 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)


def replace_filename_chars(s):
    forbidden_chars = "<>:\"/\\|?*"
    other_chars = "+$^[]()%@!="
    for c in forbidden_chars:
        s = s.replace(c, "_")
    for c in other_chars:
        s = s.replace(c, "")

    return s


def check_vertica_conn(vertica_conn):
    test_query = "select version();"
    res = False
    try:
        curr = vertica_conn.cursor()
        tr = curr.execute(test_query)
        tr = curr.fetchall()
        log.info(tr)
        curr.close()
        res = True
    except Exception as e:
        log.error(e)
        res = False
    return res


def connect_to_vertica(vertica_conn_info, current_conn=False):
    check_conn_res = False
    if current_conn: check_conn_res = check_vertica_conn(current_conn)
    if check_conn_res:
        log.warn("Current connection appears to be OK")
        try:
            log.info("Committing..")
            current_conn.commit()
        except Exception as e:
            log.error(e)
        return current_conn
    else:
        if current_conn:
            try:
                log.warn("Closing old connection")
                current_conn.commit()
                current_conn.close()
            except Exception as e:
                log.warn(e)

    log.info("Connecting to vertica....", vertica_conn_info['host'])
    vertica_conn = False
    try:
        vertica_conn = vertica_python.connect(**vertica_conn_info)
    except Exception:
        e = get_exception()
        log.error(e)
        errors.append(e)

    log.warn("Reconnected to vertica!!!!")
    return vertica_conn


SELECT = """select * from ... where status not ilike 'Active'"""
COLUMN_LIST = ["id", "name", "indicator", "ci_id", "unit", "status", "description", "trend", "type", "is_key",
               "aggregation", "color", "schedule", "display_name", "dashboard_n", "meas_tier",
               "is_flat", "is_positive", "hide_bl", "start_data", "poll_interval", "lifecycle_type",
               "ext_source", "ext_id", "ext_link", "properties", "TM", "format_value", "format_value",
               "repeat_last", "value_min", "value_max", "tm_changed", "analyze_anomaly"]
errors = []

# Параметры подключения к Vertica
vertica_conn_info = {'host': '...',
                     'port': 5433,
                     'user': '...',
                     'password': '...',
                     'database': '...',
                     'unicode_error': 'strict',
                     'connection_load_balance': True,
                     'session_label': '...',
                     'backup_server_node': ['...', '...'],
                     'ssl': False,
                     'connection_timeout': 10}

script_name = str(__file__).split(os.path.sep)[-1]
script_location = os.path.dirname(os.path.realpath(__file__)) + os.path.sep

log = customlogger.customlogger(logname=script_name,
                                filename=script_name + replace_filename_chars(("_").join(sys.argv[1:])) + ".log",
                                logpath=script_location + "log" + os.path.sep,
                                level="DEBUG", maxBytes=4000000, backupCount=10)

log.info('Starting...')
log.info(script_location, sys.argv)

# Подключаемся к вертике 
vert_con = False
vert_cur = False
try:
    vert_con = connect_to_vertica(vertica_conn_info, current_conn=vert_con)
    vert_cur = vert_con.cursor()
    log.info('Connect to Vertica: success')
except Exception:
    e = get_exception()
    log.error(e)
    errors.append(e)

dict_id = {}

try:
    log.info("Try execute:", SELECT)
    vert_cur.execute(SELECT)  # Пробуем выполнить
    vd = vert_cur.fetchall()
    log.info("Got %s rows from Vertica" % len(vd))
    if len(COLUMN_LIST) - len(vd[0]) == 1:
        for row in vd:
            dict_id[str(row[0])] = {}
            for column in range(1, len(COLUMN_LIST)):
                if column != len(COLUMN_LIST) - 1:
                    dict_id[str(row[0])][str(COLUMN_LIST[column])] = str(row[column])
    vert_con.close()
    log.info("Close connection to Vertica")
except Exception:
    e = get_exception()
    log.error(e)
    errors.append(e)

sentinel = Sentinel([('...', 26379)], socket_timeout=0.1)
master = sentinel.master_for('master01', socket_timeout=0.1, password="...", db=1)

try:
    for key in dict_id:
        master.hmset(key, dict_id[key])
        master.pexpire(key, 1000000000)
    log.info("Set %s keys to Redis" % len(dict_id))
except Exception:
    e = get_exception()
    log.error(e)
    errors.append(e)

log.info("Finished..")
