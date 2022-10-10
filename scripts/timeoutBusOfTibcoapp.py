import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import re

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

endpoint = f"https://.../_xpack/sql?format=csv"

headers = {'Accept': 'application/json', 'Content-type': 'application/json'}

cnt = 0

query = ("""
{"query": "select hostname_object, timestamp, log_name,logger_message, '~@~' from \\"...\\" 
where query ('logger_message:(\\"таймаут ожидания ответа от сервиса\\") AND (\\"DrlLogger\\")', 
'default_operator=and;default_field=logger_message') and hostname_object = '...'",
"filter": {
  "range": {
    "@timestamp": { "gte": "now-15m"
    }
    }
    }
  
}
}
""").encode('utf-8')
timeout = "n/a"
r = requests.get(endpoint, data=query, auth=('...', '...'), verify=False, headers=headers)

if r.status_code == 200:
    listRequests = r.text.split("~@~")
    dictResult = {}
    for line in listRequests:
        if re.search(r'message=таймаут ожидания ответа от сервиса (.*),', line):
            key = re.search(r'message=таймаут ожидания ответа от сервиса (.*), ', line)
            if key.group(1) not in dictResult:
                dictResult[key.group(1)] = 1
            else:
                dictResult[key.group(1)] += 1
    timeout = 0
    if dictResult != {}:
        for key in dictResult:
            timeout += dictResult[key]
            print('Service:', key, '=', dictResult[key])
    print('Timeout:', timeout)
else:
    print('Timeout:', timeout)
    print('RequestStatus:', r.status_code)
    print('RequestText:', r.text)
