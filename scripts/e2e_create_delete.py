"""End-to-end simulated browser test (requests-based).

Creates and then deletes a Resource, Story, and Symbolic Item via the admin UI.

Run with:
  PYTHONPATH=/home/james/projects/unda /.venv/bin/python scripts/e2e_create_delete.py
"""
import re
import sys
from bs4 import BeautifulSoup
import requests

BASE='http://127.0.0.1:5000'

def extract_csrf(html):
    m = re.search(r'name=["\']csrf_token["\'] value=["\']([^"\']+)["\']', html)
    return m.group(1) if m else None

def find_create_link(html):
    soup = BeautifulSoup(html, 'html.parser')
    a = soup.find('a', string=re.compile(r'Create|Add New|Create First', re.I))
    return a['href'] if a else None

def find_item_delete_action(list_html, title):
    soup = BeautifulSoup(list_html, 'html.parser')
    # find element containing title text, then the closest form
    el = soup.find(string=re.compile(re.escape(title)))
    if not el:
        return None
    parent = el.parent
    # traverse up to find a form with method POST nearby
    for _ in range(6):
        if parent is None:
            break
        form = parent.find('form', method=lambda v: v and v.lower()=='post')
        if form and form.get('action'):
            return form['action'], str(form)
        parent = parent.parent
    return None

def run():
    s = requests.Session()
    # assume test_admin exists; if not, run scripts/reproduce_toolkit_create.py separately

    # login
    r = s.get(BASE + '/auth/login')
    csrf = extract_csrf(r.text)
    r = s.post(BASE + '/auth/login', data={'username':'test_admin','password':'TestPass1234','csrf_token':csrf})
    print('login', r.status_code)

    created = []

    # Helper to create then delete
    def create_and_delete(list_path, create_via_anchor=True, create_payload=None, created_title=None):
        print('\nVisiting list', list_path)
        rl = s.get(BASE + list_path)
        if rl.status_code != 200:
            print('failed to open', list_path, rl.status_code); return False
        if create_via_anchor:
            href = find_create_link(rl.text)
            if not href:
                print('no create link found on', list_path); return False
            form_page = s.get(BASE + href)
        else:
            form_page = rl

        csrf = extract_csrf(form_page.text)
        payload = create_payload or {}
        if csrf:
            payload['csrf_token'] = csrf
        resp = s.post(form_page.url, data=payload)
        print('create POST', resp.status_code, '->', form_page.url)
        # verify by listing again
        listing = s.get(BASE + list_path)
        if created_title and created_title in listing.text:
            print('Created', created_title)
            # find delete action
            res = find_item_delete_action(listing.text, created_title)
            if not res:
                print('Could not find delete form for', created_title); return False
            action, form_html = res
            # extract csrf from listing or form_html
            csrf_local = extract_csrf(form_html) or extract_csrf(listing.text)
            post_url = action if action.startswith('http') else BASE + action
            del_data = {}
            if csrf_local:
                del_data['csrf_token'] = csrf_local
            dresp = s.post(post_url, data=del_data)
            print('delete POST', dresp.status_code, '->', post_url)
            return dresp.status_code in (200,302)
        else:
            print('Creation verification failed for', created_title)
            return False

    # Resource
    ok = create_and_delete('/admin/resources', create_payload={'title':'E2E Test Resource','url':'/tmp','description':'desc','tags':'[]'}, created_title='E2E Test Resource')
    print('resource ok', ok)

    # Story
    ok = create_and_delete('/admin/stories', create_payload={'title':'E2E Test Story','excerpt':'ex','content':'ct','featured_image':''}, created_title='E2E Test Story')
    print('story ok', ok)

    # Symbolic item
    ok = create_and_delete('/admin/symbolic-items', create_payload={'item_name':'E2E Test SI','item_type':'General','total_quantity':'10','description':'desc'}, created_title='E2E Test SI')
    print('symbolic item ok', ok)

if __name__ == '__main__':
    run()
