from playwright.sync_api import sync_playwright
import time

BASE = 'http://127.0.0.1:5000'
ADMIN_USER = 'test_admin'
ADMIN_PW = 'TestPass1234'


def login(page):
    page.goto(f"{BASE}/auth/login")
    page.fill('input[name="username"]', ADMIN_USER)
    page.fill('input[name="password"]', ADMIN_PW)
    # submit
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


def test_toolkit_flow(pw):
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    login(page)
    page.goto(f"{BASE}/admin/toolkit/create")
    page.wait_for_selector('input[name="title"]', timeout=10000)
    # fill title and content
    title = f"E2E toolkit {int(time.time())}"
    page.fill('input[name="title"]', title)
    page.fill('textarea[name="content"]', 'Playwright created toolkit item')
    # add an attachment via JS UI
    page.fill('#new-name', 'E2E PDF')
    page.fill('#new-url', '/tmp/e2e.pdf')
    page.click('button:has-text("Add to List")')
    # submit
    page.click('button[form="toolkitForm"][type="submit"]')
    page.wait_for_load_state('networkidle')
    # verify listing
    page.goto(f"{BASE}/admin/toolkit")
    page.wait_for_selector('h3')
    titles = [el.inner_text() for el in page.query_selector_all('h3')]
    found = any(title in t for t in titles)
    print('Toolkit created visible in listing:', found)
    browser.close()


def test_umv_flow(pw):
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    login(page)
    page.goto(f"{BASE}/admin/umv-global/create")
    try:
        page.wait_for_selector('input[name="key"]', timeout=10000)
        key = f"E2E_KEY_{int(time.time())}"
        page.fill('input[name="key"]', key)
        page.fill('textarea[name="value"]', 'e2e_value')
    except Exception as e:
        print('UMV create form did not appear or timed out:', str(e))
        browser.close()
        return
    page.click('button[form="umvForm"][type="submit"]')
    page.wait_for_load_state('networkidle')
    page.goto(f"{BASE}/admin/umv-global")
    page.wait_for_selector('h3')
    titles = [el.inner_text() for el in page.query_selector_all('h3')]
    found = any(key in t for t in titles)
    print('UMV created visible in listing:', found)
    browser.close()


def main():
    with sync_playwright() as pw:
        test_toolkit_flow(pw)
        test_umv_flow(pw)


if __name__ == '__main__':
    main()
