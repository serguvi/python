import time
from redis.sentinel import Sentinel

sentinel = Sentinel([('...', 26379)], socket_timeout=0.1)
masterhost = sentinel.discover_master('master01')[0]
slavehost = sentinel.discover_slaves('master01')[0][0]

master = sentinel.master_for('master01', socket_timeout=0.1, password="...")
# print(master.set('test-key', 'test-value'))
slave = sentinel.slave_for('master01', socket_timeout=0.1, password='...')
info = {}
for i in master.info():
    info[i] = master.info()[i]
print("Master:", masterhost)
print("used_memory:", info["used_memory"])
print("Загрузка maxmemory:", round(info["used_memory"] / info["maxmemory"] * 100, 2), "%")
print("rdb_last_save_time:", time.strftime("%a, %d-%m-%Y %H:%M:%S", time.localtime(info["rdb_last_save_time"])))
print("C последнего дампа прошло:", round(time.time() - info["rdb_last_save_time"]), "сек")
print("rdb_changes_since_last_save:", info["rdb_changes_since_last_save"])
print("connected_slaves:", info["connected_slaves"])
print("connected_clients:", info["connected_clients"])
print(":", info["connected_clients"])

for i in slave.info():
    info[i] = slave.info()[i]
print("\nSlave:", slavehost)
print("used_memory:", info["used_memory"])
print("Загрузка maxmemory:", round(info["used_memory"] / info["maxmemory"] * 100, 2), "%")
print("rdb_last_save_time:", time.strftime("%a, %d-%m-%Y %H:%M:%S", time.localtime(info["rdb_last_save_time"])))
print("C последнего дампа прошло:", round(time.time() - info["rdb_last_save_time"]), "сек")
print("rdb_changes_since_last_save:", info["rdb_changes_since_last_save"])
print("connected_slaves:", info["connected_slaves"])
print("connected_clients:", info["connected_clients"])
