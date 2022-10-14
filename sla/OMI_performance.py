import requests
import datetime
from slamodule import *


def main():
    logs_path = get_logs_path()
    log = get_logger("OMI_performance", logs_path)
    log.info("========START========")

    date_now = datetime.date.today()
    datetime_end = datetime.datetime(date_now.year, date_now.month, date_now.day)

    timestamp_end = round(datetime_end.timestamp(), 3)

    offset = int(datetime.datetime.today().timestamp()) - int(timestamp_end)

    # URL_Availability_omi{metric_name="Omi_test_0600balance/Login_AuthorizationForm/Status"}[24h] offset {смещение_до_конца_прошлых_суток_в_секундах}s
    requestURL_SLO_Omi_test_0600balance = f"http://............./select/3/prometheus/api/v1/query?query=" \
                                          f"URL_Availability_omi%7Bmetric_name%3D%22Omi_test_0600balance%2F" \
                                          f"Login_AuthorizationForm%2FStatus%22%7D%5B24h%5D%20offset%20{offset}s"

    # DB_Request_Result{instance_name="[Мониторинг поступления событий в БД OMI]", metric_name="number_of_events_in_5_minutes"}[24h] offset {смещение_до_конца_прошлых_суток_в_секундах}s
    requestURL_SLO_event_handling_health = f"http://............./select/3/prometheus/api/v1/query?query=" \
                                           f"DB_Request_Result%7Binstance_name%3D%22%5B%D0%9C%D0%BE%D0%BD%D0%B8%" \
                                           f"D1%82%D0%BE%D1%80%D0%B8%D0%BD%D0%B3%20%D0%BF%D0%BE%D1%81%D1%82%D1%8" \
                                           f"3%D0%BF%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F%20%D1%81%D0%BE%D0%B1%D1%8B%D1" \
                                           f"%82%D0%B8%D0%B9%20%D0%B2%20%D0%91%D0%94%20OMI%5D%22%2C%20metric_name" \
                                           f"%3D%22number_of_events_in_5_minutes%22%7D%5B24h%5D%20offset%20{offset}s"

    slo1 = None
    slo2 = None
    try:
        response_SLO_Omi_test_0600balance = requests.get(requestURL_SLO_Omi_test_0600balance)
        response_SLO_event_handling_health = requests.get(requestURL_SLO_event_handling_health)

        if response_SLO_Omi_test_0600balance.status_code == 200:
            response_json = response_SLO_Omi_test_0600balance.json()
            log.info(f"Полученный JSON Из Виктории для 'Omi_test_0600balance': {response_json}")
            slo_object1 = Slo(response_json, "0")
            downtime1 = slo_object1.get_downtime()
            slo1 = slo_object1.get_slo()
            log.info(f"SLO Доступности консоли: {slo1}%. Downtime: {round(downtime1, 3)} мин")
            cmd_code_exit = send_to_victoria("SLO_Availability_Omi_test_0600balance", slo1)
            log.info('Результат отправки в Victoria: ' + str(cmd_code_exit))
        else:
            log.error(f"Ошибка получения данных их Виктории для 'Omi_test_0600balance'. Response:"
                      f" {response_SLO_Omi_test_0600balance.text}.")

        if response_SLO_event_handling_health.status_code == 200:
            response_json = response_SLO_event_handling_health.json()
            log.info(f"Полученный JSON Из Виктории для 'Мониторинг поступления событий в БД OMI': {response_json}")
            slo_object2 = Slo(response_json, "0")
            downtime2 = slo_object2.get_downtime()
            slo2 = slo_object2.get_slo()
            log.info(f"SLO Работоспособность обработки событий: {slo2}%. Downtime: {round(downtime2, 3)} мин")
            cmd_code_exit = send_to_victoria("SLO_Event_monitoring_OMI_DB", slo2)
            log.info('Результат отправки в Victoria: ' + str(cmd_code_exit))
        else:
            log.error(f"Ошибка получения данных их Виктории для 'Мониторинг поступления событий в БД OMI'. Response:"
                      f" {response_SLO_event_handling_health.text}.")

    except Exception as e:
        log.error(e, exc_info=True)

    if slo1 is not None and slo2 is not None:
        sla_object = Sla(slo_object1, slo_object2)
        sla = sla_object.get_sla()
        log.info(f"SLA Работоспособность OMI: {sla}%. Downtime: {round(sla_object.downtime, 3)} мин")
        cmd_code_exit = send_to_victoria("SLA_OMI_performance", sla)
        log.info('Результат отправки в Victoria: ' + str(cmd_code_exit))
    else:
        log.error(f"Невозможно рассчитать SLA, так как не рассчитаны все SLO.")

    try:
        log.info("Рассчитываем месячный SLA")
        month_sla_object = PeriodicSla("SLA_OMI_performance{calculation=\"past_days\"}", "month")
        log.info(f"Полученный JSON Из Виктории: {month_sla_object.json}")
        month_sla = month_sla_object.get_sla()
        log.info(f"SLA Работоспособность OMI за текущий месяц: {month_sla}%. "
                 f"Процент простоя за текущий месяц: {month_sla_object.get_downtime_percentage()}")
        cmd_code_exit = send_to_victoria("SLA_OMI_performance", month_sla, "month")
        log.info('Результат отправки в Victoria: ' + str(cmd_code_exit))
    except Exception as e:
        log.error(e, exc_info=True)

    try:
        log.info("Рассчитываем квартальный SLA")
        quarter_sla_object = PeriodicSla("SLA_OMI_performance{calculation=\"past_days\"}", "quarter")
        log.info(f"Полученный JSON Из Виктории: {quarter_sla_object.json}")
        quarter_sla = quarter_sla_object.get_sla()
        log.info(f"SLA Работоспособность OMI за текущий квартал: {quarter_sla}%. "
                 f"Процент простоя за текущий квартал: {quarter_sla_object.get_downtime_percentage()}")
        cmd_code_exit = send_to_victoria("SLA_OMI_performance", quarter_sla, "quarter")
        log.info('Результат отправки в Victoria: ' + str(cmd_code_exit))

    except Exception as e:
        log.error(e, exc_info=True)

    log.info("========END========")


if __name__ == '__main__':
    main()
