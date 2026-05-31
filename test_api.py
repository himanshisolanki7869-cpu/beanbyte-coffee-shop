import requests
from pprint import pprint
import time

BASE = 'http://127.0.0.1:5000'

def check_menu():
    r = requests.get(f'{BASE}/api/menu')
    print('\nGET /api/menu', r.status_code)
    pprint(r.json())

def check_contact():
    payload = {
        'name': f'Test User {int(time.time())}',
        'email': 'test@example.com',
        'message': 'This is a test message from automated test.'
    }
    r = requests.post(f'{BASE}/api/contact', json=payload)
    print('\nPOST /api/contact', r.status_code)
    try:
        pprint(r.json())
    except Exception:
        print(r.text[:200])

def check_order():
    payload = {
        'items': [ {'id':'cappuccino','qty':2}, {'id':'mocha','qty':1} ],
        'total': 180*2 + 250*1,
        'customer': {
            'name': 'API Test Customer',
            'phone': '+91 98765 43210',
            'fulfillment': 'pickup'
        }
    }
    r = requests.post(f'{BASE}/api/order', json=payload)
    print('\nPOST /api/order', r.status_code)
    pprint(r.json())
    return r.json().get('order_id')

def check_orders_list():
    r = requests.get(f'{BASE}/api/orders')
    print('\nGET /api/orders', r.status_code)
    try:
        pprint(r.json())
    except Exception:
        print(r.text[:200])

def check_root():
    r = requests.get(BASE)
    print('\nGET /', r.status_code)
    if r.status_code == 200:
        ok = '<title>BeanByte Coffee Shop' in r.text
        print('Root contains expected title:', ok)

if __name__ == '__main__':
    print('Running API tests against', BASE)
    check_menu()
    check_contact()
    order_id = check_order()
    print('\nCreated order id:', order_id)
    check_orders_list()
    check_root()
