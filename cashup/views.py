from django.shortcuts import render
from social_django.models import UserSocialAuth
from datetime import datetime
from dateutil.parser import parse as date_parse
from django.conf import settings
import requests
import json

def vend_api_url(shop, resource, id=None):
    resources = {'register-list': 'api/2.0/registers',
                 'register': 'api/2.0/registers/{}'.format(id),
                 'register-sales-list': 'api/register_sales'}
    return 'https://{0}.vendhq.com/{1}'.format(shop, resources[resource])

def get_headers(token):
    return {'Authorization': 'Bearer {}'.format(token),
               'Content-Type': 'application/json',
               'Accept': 'application/json',
               'User-Agent': 'CashItUp'}

def get_shop_and_token(user):
    u = UserSocialAuth.objects.get(user=user)
    shop = u.extra_data['domain_prefix']
    token = u.extra_data['access_token']
    if 'expires' in u.extra_data:
        expiry = datetime.fromtimestamp(u.extra_data['expires'])
        if expiry < datetime.now():
            # do something
            pass
    return (shop, token)

def get_vend_registers(user):
    shop, token = get_shop_and_token(user)
    headers = get_headers(token)
    r = requests.get(vend_api_url(shop, 'register-list'), headers=headers)
    data = json.loads(r.text)
    return data.get('data', []) if isinstance (data, dict) else []

def get_vend_register(user, reg_id):
    shop, token = get_shop_and_token(user)
    headers = get_headers(token)
    r = requests.get(vend_api_url(shop, 'register', reg_id), headers=headers)
    data = json.loads(r.text)
    return data.get('data', []) if isinstance (data, dict) else []

def get_sales_data(user, since=None):
    shop, token = get_shop_and_token(user)
    headers = get_headers(token)
    url = vend_api_url(shop, 'register-sales-list')
    if since:
        url += '?since={}'.format(since)
    r = requests.get(url, headers=headers)
    data = json.loads(r.text)

    return data.get('register_sales', []) if isinstance (data, dict) else []

def select_register(request):
    reg_data = get_vend_registers(request.user)
    registers = [{'name': reg['name'],
                  'id': reg['id'],
                  'open_since': date_parse(reg['register_open_time'])} \
                        for reg in reg_data if reg['is_open']]

    return render(request, 'cashup/select_register.html',
                  {'registers': registers})

def set_register_takings(request, register_id):
    reg = get_vend_register(request.user, register_id)
    register = {'name': reg['name'],
                'open_since': date_parse(reg['register_open_time'])}
    sales = get_sales_data(request.user)
    cash_sales = 0
    card_sales = 0
    total_sales = 0
    for sale in sales:
        if sale['register_id'] == register_id:
            total_sales += sale['totals']['total_payment']
            for payment in sale['register_sale_payments']:
                if payment['name'] == 'Cash':
                    cash_sales += payment['amount']
                if payment['name'] == 'Credit Card':
                    card_sales += payment['amount']
    return render(request, 'cashup/set_register_takings.html',
                  {'register': register,
                   'cash_sales': cash_sales,
                   'card_sales': card_sales,
                   'total_sales': total_sales})
