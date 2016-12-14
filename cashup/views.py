from django.shortcuts import render
from social_django.models import UserSocialAuth
from datetime import datetime, timedelta
from dateutil.parser import parse as date_parse
from django.conf import settings
from django.utils import timezone
import requests
import json
from .models import Register, Outlet

# Helper functions

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

def get_date_or_None(possible_date):
    if not possible_date or possible_date == "null":
        return None
    return date_parse(possible_date)

def save_vend_register(user, reg_dict):
    register = Register(id=reg_dict['id'],
                        vend_user=UserSocialAuth.objects.get(user=user),
                        name=reg_dict['name'],
                        outlet=Outlet.objects.get(id=reg_dict['outlet_id']),
                        is_open=reg_dict['is_open'],
                        open_time=get_date_or_None(
                                        reg_dict['register_open_time']),
                        close_time=get_date_or_None(
                                        reg_dict['register_close_time']))
    register.save()
    return register

def get_vend_registers(user):
    shop, token = get_shop_and_token(user)
    headers = get_headers(token)
    r = requests.get(vend_api_url(shop, 'register-list'), headers=headers)
    data = json.loads(r.text)

    for reg in data.get('data', []) if isinstance (data, dict) else []:
        outlet = Outlet(id=reg['outlet_id'])
        outlet.save()
        register = save_vend_register(user, reg, outlet)
    return Register.objects.all()

def get_vend_register(user, reg_id):
    register = Register.objects.get(id=reg_id)
    if register.updated < (timezone.now() - timedelta(seconds=60)):
        print("Refreshing data")
        shop, token = get_shop_and_token(user)
        headers = get_headers(token)
        r = requests.get(vend_api_url(shop, 'register', reg_id), headers=headers)
        data = json.loads(r.text)
        regsiter = save_vend_register(user, data.get('data', None))
    return register

def get_sales_data(user, since=None):
    shop, token = get_shop_and_token(user)
    headers = get_headers(token)
    url = vend_api_url(shop, 'register-sales-list')
    if since:
        url += '?since={}'.format(since)
    r = requests.get(url, headers=headers)
    data = json.loads(r.text)

    return data.get('register_sales', []) if isinstance (data, dict) else []

# Views

def select_register(request):
    registers = get_vend_registers(request.user).filter(is_open=True)

    return render(request, 'cashup/select_register.html',
                  {'registers': registers})

def set_register_takings(request, register_id):
    register = get_vend_register(request.user, register_id)

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
