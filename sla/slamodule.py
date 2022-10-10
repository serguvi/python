import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_script_location() -> Path:
    """
    Возвращает путь до директории запущенного скрипта

    :return: путь до директории запущенного скрипта
    """
    return Path(sys.argv[0]).parent


def get_logs_path() -> Path:
    """
    Возвращает путь до директории лог файлов в директории запущенного скрипта, если не было, то создаёт

    :return: путь до директории лог файлов
    """
    logs_path = get_script_location() / "logs"
    if not os.path.exists(logs_path):
        os.mkdir(logs_path)
    return logs_path


def get_logger(filename: str, logs_path: Path) -> logging.Logger:
    """
    Создаёт логгер с указанным именем в указанную директорию.

    :param filename: Имя для лог файла
    :param logs_path: путь до директории куда сохранять лог файл
    :return: Логгер
    """
    logger = logging.getLogger(filename)
    logger.setLevel(logging.INFO)
    file_handler = RotatingFileHandler(str(logs_path/f"{filename}.log"), maxBytes=40000000, backupCount=10, encoding="UTF-8")
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)s %(lineno)s %(msg)s', datefmt="%Y-%m-%dT%H:%M:%S")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def send_to_victoria(metric_name, metric_value) -> int:
    cmd = "curl -d \"%s{calculation=\\\"past_days\\\"} %i\" -X POST \"http://............./insert/3/prometheus/api/v1/import/prometheus\"" % (metric_name, metric_value)
    return os.system(cmd)


class Slo:
    """
    Класс для работы с SLO
    """
    def __init__(self, json_object, error_value: str):
        """
        Конструктор, инициализирующий необходимые атрибуты

        :param json_object: JSON объект ответа от Виктории
        :param error_value: Критичное значение для показателя
        """
        for attr, value in json_object.items():
            self.__dict__[attr] = value
        if len(self.data.get("result", [])) == 0:
            raise Exception("Из Виктории получен пустой результат, расчёт SLO невозможен.")
        self.total_downtime = 0
        self.error_value = error_value
        self.downtimes = []
        self._calculate_downtime()

    def _calculate_downtime(self) -> None:
        """
        Рассчитывает время простоя для показателя

        :return: None
        """
        if len(self.data["result"]) > 0:
            result_dict = self.data["result"][0]
            if result_dict.get("values", None) is not None:
                start_downtime = None
                for timestamp, value in result_dict["values"]:
                    if result_dict["values"][-1][0] == timestamp and start_downtime is not None \
                            and value == self.error_value:
                        self.downtimes.append((start_downtime, timestamp))
                        self.total_downtime += timestamp - start_downtime
                    elif value == self.error_value:
                        if start_downtime is None:
                            start_downtime = timestamp
                    else:
                        if start_downtime is not None:
                            self.downtimes.append((start_downtime, timestamp))
                            self.total_downtime += timestamp - start_downtime
                            start_downtime = None
        self.total_downtime /= 60

    def get_downtime(self) -> float:
        """
        Возвращает время простоя в минутах

        :return: Время простоя в минутах
        """
        return self.total_downtime

    def get_slo(self) -> float:
        """
        Рассчитывает SLO от времени простоя

        :return: SLO в процентах
        """
        return round(((1440 - self.total_downtime) / 1440) * 100, 3)


class Sla:
    """
    Класс для работы с SLA включающим два SLO по условию нормы SLO1 && SLO2
    """
    def __init__(self, slo1: Slo, slo2: Slo):
        """
        Конструктор, инициализирующий необходимые атрибуты и рассчитывающий SLA для двух SLO

        :param slo1: объект рассчитанного slo
        :param slo2: объект рассчитанного slo
        """
        self.slo_downtimes = slo1.downtimes + slo2.downtimes
        sorted(self.slo_downtimes, key=lambda downtime: downtime[0])
        self.downtime = 0
        self.downtimes = []
        self._calculate_downtime()

    def _calculate_downtime(self) -> None:
        """
        Рассчитывает и сохраняет время простоя SLA в минутах

        :return: None
        """
        if len(self.slo_downtimes) > 1:
            downtime = self.slo_downtimes[0]
            for i in range(len(self.slo_downtimes)-1):
                x = downtime
                y = (self.slo_downtimes[i+1][0], self.slo_downtimes[i+1][1])
                intersection = not ((x[1] < y[0]) or (y[1] < x[0]))
                # print(' x %s y' % ("не пересекаются", "пересекаются")[intersection])
                if intersection:
                    downtime = (min(x[0], y[0]), max(x[1], y[1]))
                    if i == len(self.slo_downtimes)-2:
                        self.downtimes.append(downtime)
                        self.downtime += (downtime[1] - downtime[0])
                else:
                    self.downtimes.append(downtime)
                    self.downtime += (downtime[1] - downtime[0])
                    downtime = self.slo_downtimes[i+1]
                    if i == len(self.slo_downtimes)-2:
                        self.downtimes.append(downtime)
                        self.downtime += (downtime[1] - downtime[0])
            self.downtime /= 60
        elif len(self.slo_downtimes) == 1:
            self.downtimes.append(self.slo_downtimes[0])
            self.downtime += (self.slo_downtimes[0][1] - self.slo_downtimes[0][0])
            self.downtime /= 60

    def get_sla(self) -> float:
        """
        Рассчитывает SLA от времени простоя

        :return: SLA в процентах
        """
        return round(((1440 - self.downtime) / 1440) * 100, 3)
