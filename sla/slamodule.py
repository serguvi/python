import datetime
import logging
import os
import sys
from calendar import monthrange
from logging.handlers import RotatingFileHandler
from pathlib import Path

import requests


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
    file_handler = RotatingFileHandler(str(logs_path/f"{filename}.log"), maxBytes=40000000,
                                       backupCount=10, encoding="UTF-8")
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)s %(lineno)s %(msg)s',
                                  datefmt="%Y-%m-%dT%H:%M:%S")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def send_to_victoria(metric_name: str, metric_value: float, calculation: str = "past_days", test: bool = False) -> int:
    """
    Отправляет метрику в викторию с помозщью curl'a

    :param metric_name: Имя метрики
    :param metric_value: Значение метрики
    :param calculation: Опционально, период расчёта
    :param test: Опционально, тест или нет
    :return: результат выполнения команды в cmd
    """
    cmd = "curl -d \"%s{calculation=\\\"%s\\\"} %.2f\" " \
          "-X POST \"http://.../insert/3/prometheus/api/v1/import/prometheus\"" \
          % (metric_name, calculation, metric_value)
    if not test:
        return os.system(cmd)
    else:
        print(cmd)
        return 0


def calculate_period_sla(metric_name_rus: str, metric_name: str, period: str, log: logging.Logger,
                         test: bool = False) -> None:
    """
    Рассчитывает и отправляет в викторию занчение SLA за указанные период в динамике

    :param metric_name_rus: Имя метрики для записи в лог
    :param metric_name: Имя метрики для отправки в викторию
    :param period: Период за который необходим расчёт (month или quarter)
    :param log: Логгер
    :param test: Опционально, тест или нет
    :return: None
    """
    if period == "quarter":
        rus_period = "квартал"
    elif period == "month":
        rus_period = "месяц"
    else:
        log.error(f"Невозможно рассчитать за период, так как не правильно указан период. Period: {period}")
        return

    try:
        log.info(f"Рассчитываем {metric_name_rus} за текущий {rus_period}")
        sla_object = PeriodicSla("%s{calculation=\"past_days\"}" % metric_name, period)
        log.info(f"Полученный JSON Из Виктории: {sla_object.json}")
        sla = sla_object.get_sla()
        downtime = sla_object.get_downtime()
        downtime_percentage = sla_object.get_downtime_percentage()
        remaining_allowable_downtime = sla_object.get_remaining_allowable_downtime()
        remaining_allowable_downtime_percentage = sla_object.get_remaining_allowable_downtime_percentage()
        log.info(f"{metric_name_rus} за текущий {rus_period}: {sla}%. \n"
                 f"\tПроцент простоя за текущий {rus_period}: {downtime_percentage}. \n"
                 f"\tВремя простоя за текущий {rus_period}: {downtime}. \n"
                 f"\tОставшееся допустимое время простоя за текущий {rus_period}: {remaining_allowable_downtime}. \n"
                 f"\tОставшееся допустимое время простоя в % за текущий {rus_period}: "
                 f"{remaining_allowable_downtime_percentage}.")
        log.info("Отправляем метрику в Victoria.")
        cmd_code_exit = send_to_victoria(metric_name, sla, period, test)
        log.info('Результат отправки в Victoria: ' + str(cmd_code_exit))
        log.info("Отправляем оставшееся допустимое время простоя в Victoria.")
        cmd_code_exit = send_to_victoria(metric_name + "_remaining_allowable_downtime",
                                         remaining_allowable_downtime, period, test)
        log.info('Результат отправки в Victoria: ' + str(cmd_code_exit))
        log.info("Отправляем оставшееся допустимое время простоя (%) в Victoria.")
        cmd_code_exit = send_to_victoria(metric_name + "_remaining_allowable_downtime_percentage",
                                         remaining_allowable_downtime_percentage, period, test)
        log.info('Результат отправки в Victoria: ' + str(cmd_code_exit))

    except Exception as e:
        log.error(e, exc_info=True)


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
        self.data = {}
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


class PeriodicSla:
    date_now = datetime.datetime.now()
    minutes_in_day = 1440
    days_in_current_month = monthrange(date_now.year, date_now.month)[1]

    allowable_downtime_percentage = 1.0

    first_quarter_start = datetime.datetime(date_now.year, 1, 1)
    second_quarter_start = datetime.datetime(date_now.year, 4, 1)
    third_quarter_start = datetime.datetime(date_now.year, 7, 1)
    fourth_quarter_start = datetime.datetime(date_now.year, 10, 1)

    def __init__(self, victoria_request: str, period: str):
        """
        Создаёт объект класса, выполняет запрос на получение данных по сла из виктории

        :param victoria_request: запрос в викторию по которому можно получить даныые по SLA
        :param period: период расчёта SLA (quarter или month)
        """
        self.victoria_request = victoria_request
        self.period = period
        self.downtime = None
        self.downtime_percentage = None
        self.allowable_downtime = None
        self.remaining_allowable_downtime = None
        self.remaining_allowable_downtime_percentage = None
        self.sla = None
        self.quarter = None
        self._set_target_days()
        self._set_data()

    def _set_target_days(self) -> None:
        """
        Вычисляет кол-во дней за которые необходимо получить данные из виктории, зависит от полученного периода

        :return: None
        """

        first_day_month = datetime.datetime(self.date_now.year, self.date_now.month, 1)

        if self.period == "quarter":
            if self.date_now > self.fourth_quarter_start:
                self.target_days = (self.date_now - self.fourth_quarter_start).days
                self.quarter = 4
            elif self.date_now > self.third_quarter_start:
                self.target_days = (self.date_now - self.third_quarter_start).days
                self.quarter = 3
            elif self.date_now > self.second_quarter_start:
                self.target_days = (self.date_now - self.second_quarter_start).days
                self.quarter = 2
            else:
                self.target_days = (self.date_now - self.first_quarter_start).days
                self.quarter = 1
        else:
            self.target_days = (self.date_now - first_day_month).days

    def _set_data(self) -> None:
        """
        Выполняет запрос в викторию, сохраняет полученный json и значения искомого SLA за необходимый период

        :return: None
        """
        request_url = f"http://.../select/3/prometheus/api/v1/query?" \
                      f"query={self.victoria_request}[{self.target_days}d]"
        self.response = requests.get(request_url)
        if self.response.status_code != 200:
            raise ValueError(f"Ошибка получения данных их Виктории для запроса '{request_url}'. "
                             f"Response: {self.response.text}.")
        self.json = self.response.json()
        self.data = self.json.get("data", {})
        self.data_result = self.data.get("result", [{}])
        if len(self.data_result) == 0:
            self.values = None
        else:
            self.values = self.data_result[0].get("values", None)
        if self.values is None:
            raise ValueError(f"Нет данных для расчёта в полученном json из виктории. JSON: {self.json}")

    def calculate_downtime_percentage(self) -> None:
        """
        Рассчитывает и сохраняет процент простоя за необходимый период

        :return: None
        """
        total_value = 0
        last_timestamp = 0
        count_values = 0
        for timestamp, value in self.values:
            if timestamp - last_timestamp > 80000:  # текущий timestamp value должен быть старше предыдущего +- на сутки
                total_value += float(value)
                last_timestamp = timestamp
                count_values += 1
        self.downtime_percentage = (count_values * 100 - total_value) / (count_values * 100) * 100

    def get_downtime_percentage(self) -> float:
        """
        Возвращает процент простоя за необходимый период

        :return: Процент простоя за необходимый период
        """
        if self.downtime_percentage is None:
            self.calculate_downtime_percentage()
        return round(self.downtime_percentage, 2)

    def calculate_sla(self) -> None:
        """
        Рассчитывает и сохраняет SLA за необходимый период

        :return: None
        """
        if self.downtime_percentage is None:
            self.calculate_downtime_percentage()

        if self.downtime_percentage <= self.allowable_downtime_percentage:
            self.sla = 100.0
        else:
            self.sla = 100.0 - self.downtime_percentage

    def get_sla(self) -> float:
        """
        Возвращает SLA за необходимый период

        :return: SLA за необходимый период
        """
        if self.sla is None:
            self.calculate_sla()
        return round(self.sla, 2)

    def calculate_downtime(self) -> None:
        """
        Рассчитывает текущее время простоя за необходимый период

        :return: None
        """
        if self.downtime_percentage is None:
            self.calculate_downtime_percentage()

        self.downtime = self.target_days * PeriodicSla.minutes_in_day * (self.downtime_percentage / 100)

    def get_downtime(self) -> float:
        """
        Возвращает текущее время простоя за необходимый период

        :return: Текущее время простоя за необходимый период
        """
        if self.downtime is None:
            self.calculate_downtime()

        return round(self.downtime, 2)

    def calculate_allowable_downtime(self) -> None:
        """
        Рассчитывает допустимое время простоя за необходимый период

        :return: None
        """
        if self.period == "month":
            days_amount = self.days_in_current_month
        else:
            if self.quarter == 4:
                days_amount = (datetime.datetime(self.date_now.year + 1, 1, 1) - self.fourth_quarter_start).days
            elif self.quarter == 3:
                days_amount = (self.fourth_quarter_start - self.third_quarter_start).days
            elif self.quarter == 2:
                days_amount = (self.third_quarter_start - self.second_quarter_start).days
            else:
                days_amount = (self.second_quarter_start - self.first_quarter_start).days
        minutes_amount = days_amount * self.minutes_in_day
        self.allowable_downtime = minutes_amount * (self.allowable_downtime_percentage / 100)

    def get_allowable_downtime(self) -> float:
        """
        Возвращает допустимое время простоя за необходимый период

        :return: Допустимое время простоя за необходимый период
        """
        if self.allowable_downtime is None:
            self.calculate_allowable_downtime()
        return round(self.allowable_downtime, 2)

    def calculate_remaining_allowable_downtime(self) -> None:
        """
        Рассчитывает оставшееся допустимое время простоя за необходимый период

        :return: None
        """
        downtime = self.get_downtime()
        allowable_downtime = self.get_allowable_downtime()
        self.remaining_allowable_downtime = allowable_downtime - downtime

    def get_remaining_allowable_downtime(self) -> float:
        """
        Возвращает оставшееся допустимое время простоя за необходимый период

        :return: Оставшееся допустимое время простоя за необходимый период
        """
        if self.remaining_allowable_downtime is None:
            self.calculate_remaining_allowable_downtime()
        return round(self.remaining_allowable_downtime, 2)

    def calculate_remaining_allowable_downtime_percentage(self) -> None:
        """
        Рассчитывает процент оставшегося допустимого времени простоя за необходимый период

        :return: None
        """
        downtime = self.get_downtime()
        allowable_downtime = self.get_allowable_downtime()
        self.remaining_allowable_downtime_percentage = 100 - (downtime / (allowable_downtime / 100))

    def get_remaining_allowable_downtime_percentage(self):
        """
        Возвращает процент оставшегося допустимого времени простоя за необходимый период

        :return: Процент оставшегося допустимого времени простоя за необходимый период
        """
        if self.remaining_allowable_downtime_percentage is None:
            self.calculate_remaining_allowable_downtime_percentage()
        return round(self.remaining_allowable_downtime_percentage, 2)
