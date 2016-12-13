from django.shortcuts import render
from social_django.models import UserSocialAuth
from datetime import datetime
from django.conf import settings
import requests
import json

def select_register(request):
    u = UserSocialAuth.objects.get(user=request.user)
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
    url = 'https://{}.vendhq.com/api/registers'.format(shop)
    r = requests.get(url, headers=headers)
    data = json.loads(r.text)

    if data and ('registers' in data) and data['registers']:
        registers = [u['name'] for u in data['registers'] if not u['register_close_time']]

    return render(request, 'cashup/select_register.html',
                  {'registers': registers})

