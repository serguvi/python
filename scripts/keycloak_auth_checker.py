import requests
from requests.structures import CaseInsensitiveDict
import json
import argparse
import sys
import urllib3


def get_token():
    params = {
        'client_id': args.client_id,
        'grant_type': 'password',
        'client_secret': args.client_secret,
        'scope': 'openid',
        'username': args.user_name,
        'password': args.password,
    }
    r1 = requests.post(args.url + '/auth/realms/{}/protocol/openid-connect/token'.format(args.realm),
                       params, verify=False).content.decode('utf-8')
    data = json.loads(r1)
    if 'access_token' not in data:
        print(data['error_description'])
        print('{"keycloak": false}')
        sys.exit(1)
    return r1


def check_auth():
    r1 = get_token()
    headers = CaseInsensitiveDict()
    headers["Cookie"] = 'keycloak-token={}'.format(r1)
    r2 = requests.get(args.app_url + '/api/auth/', verify=False, headers=headers).content.decode('utf-8')
    if "true" in r2:
        print('{"authenticated": true}')
    else:
        print('{"authenticated": false}')
        sys.exit(1)


if __name__ == '__main__':
    urllib3.disable_warnings()
    my_parser = argparse.ArgumentParser()
    my_parser.add_argument('--app-url', type=str, help='webapi url', required=True)
    my_parser.add_argument('--client-id', type=str, help='keycloak client id', required=True)
    my_parser.add_argument('--url', type=str, help='keycloak url', required=True)
    my_parser.add_argument('--password', type=str, help='keycloak password', required=True)
    my_parser.add_argument('--realm', type=str, help='keycloak realm', required=True)
    my_parser.add_argument('--client-secret', type=str, help='keycloak client secret', required=True)
    my_parser.add_argument('--user-name', type=str, help='keycloak user name', required=True)
    args = my_parser.parse_args()

    get_token()
    check_auth()
