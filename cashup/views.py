from django.shortcuts import render
from social_django.models import UserSocialAuth
from datetime import datetime, timedelta
from dateutil.parser import parse as date_parse
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse
import requests
import json
from .models import Register, Outlet, RegisterTakings, RegisterCashup
from .forms import RegisterTakingsForm, RegisterCashupForm
import uuid
import decimal

# Helper functions

def vend_api_url(shop, resource, id=None):
    resources = {'register-list': 'api/2.0/registers',
                 'register': 'api/2.0/registers/{}'.format(id),
                 'register-sales-list': 'api/register_sales',
                 'outlet': 'api/2.0/outlets/{}'.format(id),
    }
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
        outlet_id = reg['outlet_id']
        try:
            outlet = Outlet.objects.get(id=outlet_id)
        except Outlet.DoesNotExist:
            r = requests.get(vend_api_url(shop, 'outlet',
                                        id=outlet_id), headers=headers)
            outlet_data = json.loads(r.text)
            outlet_dict = outlet_data.get('data', None) if \
                                    isinstance(outlet_data, dict) else None
            if outlet_dict:
                outlet = Outlet(id=outlet_id, name=outlet_dict['name'])
                outlet.save()
        print(outlet.name)
        register = save_vend_register(user, reg)
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

def get_sales_data(user, register):
    shop, token = get_shop_and_token(user)
    headers = get_headers(token)
    since = register.open_time.replace(tzinfo=None).isoformat()
    url = vend_api_url(shop, 'register-sales-list') + '?since={}'.format(since)
    r = requests.get(url, headers=headers)
    data = json.loads(r.text)

    sales = data.get('register_sales', []) if isinstance (data, dict) else []
    sales_count = 0
    cash_sales = 0
    card_sales = 0
    total_sales = 0
    for sale in sales:
        if sale['register_id'] == str(register.id):
            sales_count += 1
            total_sales += sale['totals']['total_payment']
            for payment in sale['register_sale_payments']:
                if payment['name'] == 'Cash':
                    cash_sales += payment['amount']
                if payment['name'] == 'Credit Card':
                    card_sales += payment['amount']
    return (sales_count, cash_sales, card_sales, total_sales)

# Views

def select_register(request):
    registers = get_vend_registers(request.user).filter(is_open=True)

    return render(request, 'cashup/select_register.html',
                  {'registers': registers})

def set_register_takings(request, register_id):
    register = get_vend_register(request.user, register_id)
    count = None

    if request.method == 'POST':
        try:
            reg_takings = RegisterTakings.objects.get(register=register,
                                register_open_time=register.open_time)
        except RegisterTakings.DoesNotExist:
            reg_takings = RegisterTakings(register=register,
                                register_open_time=register.open_time)
        form = RegisterTakingsForm(request.POST, instance=reg_takings)
        if form.is_valid():
            register_takings = form.save()
            return HttpResponseRedirect(
                        reverse('cashup_register', args=[register_takings.id]))

    if register.is_open:
        count, cash, card, total = get_sales_data(request.user, register)
        form = RegisterTakingsForm(initial={'cash_takings': cash,
                                                'card_takings': card,
                                                'total_takings': total})
    else:
        form = None

    return render(request, 'cashup/set_register_takings.html',
                  {'register': register,
                   'form': form,
                   'number_of_sales': count})

def get_till_total(reg_cashup):
    total = decimal.Decimal('0.00')
    total += decimal.Decimal('50.00') * reg_cashup.note_GBP50
    total += decimal.Decimal('20.00') * reg_cashup.note_GBP20
    total += decimal.Decimal('10.00') * reg_cashup.note_GBP10
    total += decimal.Decimal('5.00') * reg_cashup.note_GBP5
    total += decimal.Decimal('2.00') * reg_cashup.coin_GBP2
    total += decimal.Decimal('1.00') * reg_cashup.coin_GBP1
    total += decimal.Decimal('0.50') * reg_cashup.coin_50p
    total += decimal.Decimal('0.20') * reg_cashup.coin_20p
    total += decimal.Decimal('0.10') * reg_cashup.coin_10p
    total += decimal.Decimal('0.05') * reg_cashup.coin_5p
    total += decimal.Decimal('0.02') * reg_cashup.coin_2p
    total += decimal.Decimal('0.01') * reg_cashup.coin_1p
    return total

def cashup_register(request, register_takings_id):
    register_takings = RegisterTakings.objects.get(id=register_takings_id)
    try:
        register_cashup = RegisterCashup.objects.get(
                                register_takings=register_takings)
    except RegisterCashup.DoesNotExist:
        register_cashup = RegisterCashup(register_takings=register_takings)

    if request.method == 'POST':
        form = RegisterCashupForm(request.POST, instance=register_cashup)
        if form.is_valid():
            reg_cashup = form.save(commit=False)
            till_total = get_till_total(reg_cashup)
            till_float = reg_cashup.till_float
            difference = till_total - register_takings.cash_takings - till_float
            reg_cashup.till_total = till_total
            reg_cashup.till_difference = difference
            reg_cashup.save()
            return HttpResponseRedirect(
                        reverse('cashup_register', args=[register_takings.id]))
    else:
        form = RegisterCashupForm(instance=register_cashup)

    return render(request, 'cashup/register_cashup.html',
                  {'register': register_takings.register,
                   'register_takings': register_takings,
                   'form': form})