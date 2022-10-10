from bottle import route, run, template, install, request, response, default_app
from mySelenium import Selenium
from logger_assistant import *
from functools import wraps
from datetime import datetime
from paste import httpserver
import logging
import socket
import time


def log_to_logger(fn):
	@wraps(fn)
	def _log_to_logger(*args, **kwargs):
		request_time = datetime.now()
		actual_response = fn(*args, **kwargs)
		logger.info('%s %s %s %s %s' % (request.remote_addr, request_time,
										request.method, request.url, response.status))
		return actual_response
	return _log_to_logger


@route('/<id>')
def index(id):
	try:
		logger.info("Создаём подключение селениума.")
		selenium_page = Selenium(id)
		logger.info("Получаем картинку карточки показателя.")
		image = selenium_page.get_image()
		logger.info("Завершаем работу селениума")
		selenium_page.quit()
		png_remover(script_location, logger)
	except Exception as e:
		logger.error(e)
	return template('<img src="data:image/png;base64,{{image}}"/>', image=image)


@route('/graphic/<id>')
def graphic(id):
	try:
		logger.info("Создаём подключение селениума.")
		selenium_page = Selenium(id)
		logger.info("Получаем картинку карточки показателя.")
		screenshot = selenium_page.get_image()
		logger.info("Получаем график показателя.")
		image = selenium_page.get_graphic()
		logger.info("Завершаем работу селениума")
		selenium_page.quit()
		png_remover(script_location, logger)
	except Exception as e:
		logger.error(e)
	return template('<img src="data:image/png;base64,{{image}}"/>', image=image)


@route('/graphic/<hour>/<id>')
def graphic_hours(hour, id):
	try:
		logger.info("Создаём подключение селениума.")
		hour_option_dict = {"1":1, "3":2, "6":3, "12":4, "24":5, "72":6, "168":7, "720":8}
		selenium_page = Selenium(id)
		logger.info("Получаем картинку карточки показателя.")
		screenshot = selenium_page.get_image(hour_option_dict.get(hour, None))
		logger.info("Получаем график показателя.")
		image = selenium_page.get_graphic()
		logger.info("Завершаем работу селениума.")
		selenium_page.quit()
		png_remover(script_location, logger)
	except Exception as e:
		logger.error(e)
	return template('<img src="data:image/png;base64,{{image}}"/>', image=image)


@route('/custom_graphic/<hour>/<id>')
def custom_graphic_hours(hour, id):
	start_time = time.time()
	try:
		logger.info("Создаём подключение селениума.")
		selenium_page = Selenium(id, hour)
		logger.info("Получаем картинку карточки показателя.")
		screenshot = selenium_page.get_custom_graphic_image()
		logger.info("Получаем график показателя.")
		#image = screenshot
		image = selenium_page.get_custom_graphic()
		logger.info("Завершаем работу селениума.")
		selenium_page.quit()
		png_remover(script_location, logger)
	except Exception as e:
		logger.error(e)
	execute_time = round(time.time() - start_time, 6)
	logger.info(f"Execute time: {execute_time}")
	response.set_header('X-Execution-Time', str(execute_time))
	return template('<img src="data:image/png;base64,{{image}}"/>', image=image)


@route('/statuses/<id>')
def graphic(id):
	start_time = time.time()
	try:
		logger.info("Создаём подключение селениума.")
		selenium_page = Selenium(id)
		logger.info("Получаем картинку карточки показателя.")
		screenshot = selenium_page.get_image()
		logger.info("Получаем статусы показателя за 30 дней.")
		image = selenium_page.get_statuses()
		logger.info("Завершаем работу селениума")
		selenium_page.quit()
		png_remover(script_location, logger)
	except Exception as e:
		logger.error(e)
	execute_time = round(time.time() - start_time, 6)
	logger.info(f"Execute time: {execute_time}")
	response.set_header('X-Execution-Time', str(execute_time))
	return template('<img src="data:image/png;base64,{{image}}"/>', image=image)


script_location = get_script_location()
script_name = get_script_name()
log_path = make_and_get_logs_path()

logger = get_logger("bottle", log_path)

install(log_to_logger)
logger.info("Старт приложения")
host = socket.gethostbyname(socket.gethostname())
application = default_app()
httpserver.serve(application, host=host, port=8443)

