import datetime

import requests

import slamodule


def main():
    logs_path = slamodule.get_logs_path()
    log = slamodule.get_logger("Fault_tolerance_OMi_GW", logs_path)
    log.info("========START========")

    date_now = datetime.date.today()
    datetime_end = datetime.datetime(date_now.year, date_now.month, date_now.day)

    timestamp_end = round(datetime_end.timestamp(), 3)

    offset = int(datetime.datetime.today().timestamp()) - int(timestamp_end)

    # URL_Availability_omi{metric_name="Omi_test_GW1/Login_AuthorizationForm/Status"}[24h]
    # offset {смещение_до_конца_прошлых_суток_в_секундах}s
    request_url_slo_omi_test_gw1 = f"http://............./select/3/prometheus/api/v1/query?query=" \
                                   f"URL_Availability_omi%7Bmetric_name%3D%22Omi_test_GW1%2F" \
                                   f"Login_AuthorizationForm%2FStatus%22%7D%5B24h%5D%20offset%20{offset}s"

    # URL_Availability_omi{metric_name="Omi_test_GW2/Login_AuthorizationForm/Status"}[24h]
    # offset {смещение_до_конца_прошлых_суток_в_секундах}s
    request_url_slo_omi_test_gw2 = f"http://............./select/3/prometheus/api/v1/query?query=" \
                                   f"URL_Availability_omi%7Bmetric_name%3D%22Omi_test_GW2%2F" \
                                   f"Login_AuthorizationForm%2FStatus%22%7D%5B24h%5D%20offset%20{offset}s"

    slo1, slo2 = None, None
    slo_object1, slo_object2 = None, None
    try:
        response_slo_omi_test_gw1 = requests.get(request_url_slo_omi_test_gw1)
        response_slo_omi_test_gw2 = requests.get(request_url_slo_omi_test_gw2)

        if response_slo_omi_test_gw1.status_code == 200:
            response_json = response_slo_omi_test_gw1.json()
            log.info(f"Полученный JSON Из Виктории для 'Omi_test_GW1': {response_json}")
            slo_object1 = slamodule.Slo(response_json, "0")
            downtime1 = slo_object1.get_downtime()
            slo1 = slo_object1.get_slo()
            log.info(f"SLO Доступность GW1: {slo1}%. Downtime: {round(downtime1, 3)} мин")
            cmd_code_exit = slamodule.send_to_victoria("SLO_Omi_test_GW1", slo1)
            log.info('Результат отправки в Victoria: ' + str(cmd_code_exit))
            slamodule.calculate_period_sla("SLO Доступность GW1",
                                           "SLO_Omi_test_GW1", "month", log)
            slamodule.calculate_period_sla("SLO Доступность GW1",
                                           "SLO_Omi_test_GW1", "quarter", log)
        else:
            log.error(f"Ошибка получения данных их Виктории для 'Omi_test_GW1'. Response:"
                      f" {response_slo_omi_test_gw1.text}.")

        if response_slo_omi_test_gw2.status_code == 200:
            response_json = response_slo_omi_test_gw2.json()
            log.info(f"Полученный JSON Из Виктории для 'Omi_test_GW2': {response_json}")
            slo_object2 = slamodule.Slo(response_json, "0")
            downtime2 = slo_object2.get_downtime()
            slo2 = slo_object2.get_slo()
            log.info(f"SLO Доступность GW2: {slo2}%. Downtime: {round(downtime2, 3)} мин")
            cmd_code_exit = slamodule.send_to_victoria("SLO_Omi_test_GW2", slo2)
            log.info('Результат отправки в Victoria: ' + str(cmd_code_exit))
            slamodule.calculate_period_sla("SLO Доступность GW2", "SLO_Omi_test_GW2",
                                           "month", log)
            slamodule.calculate_period_sla("SLO Доступность GW2", "SLO_Omi_test_GW2",
                                           "quarter", log)
        else:
            log.error(f"Ошибка получения данных их Виктории для 'Omi_test_GW2'. Response:"
                      f" {response_slo_omi_test_gw2.text}.")

    except Exception as e:
        log.error(e, exc_info=True)

    if slo1 is not None and slo2 is not None:
        sla_object = slamodule.Sla(slo_object1, slo_object2)
        sla = sla_object.get_sla()
        log.info(f"SLA Отказоустойчивость OMi GW: {sla}%. Downtime: {round(sla_object.downtime, 3)} мин")
        cmd_code_exit = slamodule.send_to_victoria("SLA_Fault_tolerance_OMi_GW", sla)
        log.info('Результат отправки в Victoria: ' + str(cmd_code_exit))
    else:
        log.error("Невозможно рассчитать SLA, так как не рассчитаны все SLO.")

    slamodule.calculate_period_sla("SLA Отказоустойчивость OMi GW", "SLA_Fault_tolerance_OMi_GW", "month", log)
    slamodule.calculate_period_sla("SLA Отказоустойчивость OMi GW", "SLA_Fault_tolerance_OMi_GW", "quarter", log)

    log.info("========END========")


if __name__ == '__main__':
    main()
