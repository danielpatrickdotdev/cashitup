from django.shortcuts import render
from social_django.models import UserSocialAuth
from datetime import datetime
from dateutil.parser import parse as date_parse
from django.conf import settings
import requests
import json

def vend_api_url(shop, resource):
    resources = {'register-list': 'api/registers'}
    return 'https://{0}.vendhq.com/{1}'.format(shop, resources[resource])

def get_vend_registers(user):
    u = UserSocialAuth.objects.get(user=user)
    shop = u.extra_data['domain_prefix']
    token = u.extra_data['access_token']
    if 'expires' in u.extra_data:
        expiry = datetime.fromtimestamp(u.extra_data['expires'])
        if expiry < datetime.now():
            # do something
            pass

    headers = {'Authorization': 'Bearer {}'.format(token),
               'Content-Type': 'application/json',
               'Accept': 'application/json'}
    r = requests.get(vend_api_url(shop, 'register-list'), headers=headers)
    data = json.loads(r.text)

    return data.get('registers', []) if isinstance (data, dict) else []

def select_register(request):
    reg_data = get_vend_registers(request.user)
    registers = [{'name': reg['name'],
                  'open_since': date_parse(reg['register_open_time'])} \
                        for reg in reg_data if not reg['register_close_time']]

    return render(request, 'cashup/select_register.html',
                  {'registers': registers})

