"""Minimal mass E2E tester (skeleton).

This file will be expanded in follow-up commits. It contains a minimal runnable
entrypoint so the project can commit changes in stages.
"""

def main():
    print('e2e_mass_admin skeleton')


if __name__ == '__main__':
    main()


def extract_csrf(html):
    m = re.search(r'name=["\']csrf_token["\'] value=["\']([^"\']+)["\']', html)
    return m.group(1) if m else None


def find_create_link(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Prioritize links that include 'create' or 'add'
    a = soup.find('a', string=re.compile(r'create|add new|add|create first', re.I))
    if a and a.get('href'):
        return a['href']
    # fallback: look for buttons with role=button
    a = soup.find('a', href=True)
    return a['href'] if a else None


def fill_form(soup, page_label):
    data = {}
    for inp in soup.find_all(['input', 'select', 'textarea']):
        name = inp.get('name')
        if not name:
            continue
        t = inp.name
        itype = inp.get('type', '').lower()
        if itype in ('file', 'password'):
            # skip file uploads and password fields
            continue
        if itype == 'checkbox':
            data[name] = inp.get('value') or 'on'
            continue
        if t == 'select':
            # choose first non-empty option
            opt = inp.find('option', value=lambda v: v and v.strip()!='') or inp.find('option')
            if opt:
                data[name] = opt.get('value') or opt.text.strip()
            continue
        # Heuristic values
        lname = name.lower()
        if 'title' in lname or 'name' in lname or 'subject' in lname:
            data[name] = f'E2E {page_label} {datetime.utcnow().strftime("%Y%m%d%H%M%S")}'
        elif 'content' in lname or 'description' in lname or 'excerpt' in lname or 'body' in lname:
            data[name] = f'Automated content for {page_label} at {datetime.utcnow().isoformat()}'
        elif 'url' in lname or 'link' in lname or lname.endswith('_path'):
            data[name] = '/tmp'
        elif 'quantity' in lname or 'count' in lname or 'total' in lname or 'number' in lname:
            data[name] = '10'
        elif itype == 'number':
            data[name] = '1'
        else:
            # fallback short text
            data[name] = f'val-{name[:10]}'
    return data


def find_delete_form_and_action(listing_html, created_label):
    soup = BeautifulSoup(listing_html, 'html.parser')
    el = soup.find(string=re.compile(re.escape(created_label)))
    if not el:
        return None
    parent = el.parent
    for _ in range(8):
        if parent is None:
            break
        form = parent.find('form', method=lambda v: v and v.lower() == 'post')
        if form and form.get('action'):
            return form.get('action'), str(form)
        parent = parent.parent
    # fallback: find any form with a delete route
    for f in soup.find_all('form'):
        a = f.get('action','')
        if 'delete' in a or 'remove' in a or 'delete' in str(f).lower():
            return a, str(f)
    return None


def run_one_listing(session, path):
    logger.info('Testing listing %s', path)
    r = session.get(BASE + path)
    if r.status_code != 200:
        logger.warning('Failed to GET listing %s -> %s', path, r.status_code)
        return False
    adapter = ADAPTERS.get(path)
    if adapter and adapter.get('create_url'):
        create_url = BASE + adapter['create_url']
    else:
        create_href = find_create_link(r.text)
        if not create_href:
            logger.info('No create link found for %s; skipping', path)
            return False
        # Resolve create URL
        create_url = create_href if create_href.startswith('http') else BASE + create_href
    logger.info('Visiting create form %s', create_url)
    form_page = session.get(create_url)
    if form_page.status_code != 200:
        logger.warning('Failed to load create form %s -> %s', create_url, form_page.status_code)
        return False
    # parse form
    soup = BeautifulSoup(form_page.text, 'html.parser')
    form = soup.find('form')
    # build payload (adapter may expect form soup or None)
    if adapter and adapter.get('payload'):
        payload_builder = adapter['payload']
        try:
            payload = payload_builder(form)
        except Exception:
            payload = payload_builder(None)
    else:
        if form:
            payload = fill_form(form, path.strip('/').replace('/', '-') or 'admin')
        else:
            payload = {}

    # csrf token: prefer create form, fall back to listing page
    csrf = extract_csrf(form_page.text) or extract_csrf(r.text)
    if csrf:
        payload['csrf_token'] = csrf
    # send POST to form action
    action = form.get('action') if form and form.get('action') else create_url
    post_url = action if action.startswith('http') else BASE + action
    logger.info('Submitting create POST to %s with %d fields', post_url, len(payload))
    post = session.post(post_url, data=payload)
    logger.info('Create response %s', post.status_code)
    time.sleep(0.5)
    # verify in listing
    listing = session.get(BASE + path)

    # If adapter provided a verify hook, use it
    if adapter and adapter.get('verify'):
        v = adapter['verify']
        if isinstance(v, str):
            # named verify functions defined above
            if v == 'verify_toolkit':
                res = verify_toolkit(listing.text, payload)
                if res:
                    action, form_html = res
                    csrf_local = extract_csrf(form_html) or extract_csrf(listing.text)
                    del_url = action if action.startswith('http') else BASE + action
                    del_data = {}
                    if csrf_local:
                        del_data['csrf_token'] = csrf_local
                    dresp = session.post(del_url, data=del_data)
                    logger.info('Delete POST %s -> %s', dresp.status_code, del_url)
                    return dresp.status_code in (200, 302)
                else:
                    logger.warning('Created label not found in listing for %s', path)
                    return False
            elif v == 'verify_assessment':
                ok = verify_assessment(listing.text, payload)
                if ok:
                    logger.info('Assessment created and found in listing')
                    return True
                logger.warning('Created label not found in listing for %s', path)
                return False

    # default heuristic: look for an E2E-prefixed value in listing text
    created_label = None
    for v in payload.values():
        if isinstance(v, str) and v.startswith('E2E'):
            created_label = v
            break
    if created_label and created_label in listing.text:
        logger.info('Created %s confirmed in listing', created_label)
        # find delete
        res = find_delete_form_and_action(listing.text, created_label)
        if not res:
            logger.warning('Could not find delete form for %s', created_label)
            return True
        action, form_html = res
        csrf_local = extract_csrf(form_html) or extract_csrf(listing.text)
        del_url = action if action.startswith('http') else BASE + action
        del_data = {}
        if csrf_local:
            del_data['csrf_token'] = csrf_local
        dresp = session.post(del_url, data=del_data)
        logger.info('Delete POST %s -> %s', dresp.status_code, del_url)
        return dresp.status_code in (200, 302)
    else:
        logger.warning('Created label not found in listing for %s', path)
        return False


def main():
    s = requests.Session()
    # Login
    r = s.get(BASE + '/auth/login')
    csrf = extract_csrf(r.text)
    r = s.post(BASE + '/auth/login', data={'username': ADMIN_USER, 'password': ADMIN_PW, 'csrf_token': csrf})
    if r.status_code != 200:
        logger.error('Login failed: %s', r.status_code)
        return
    results = {}
    for p in LISTING_PATHS:
        try:
            ok = run_one_listing(s, p)
            results[p] = ok
        except Exception as e:
            logger.exception('Error testing %s: %s', p, e)
            results[p] = False

    logger.info('Summary:')
    for p,ok in results.items():
        logger.info('%s -> %s', p, 'OK' if ok else 'FAIL')


if __name__ == '__main__':
    main()
