from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.wait import WebDriverWait

import time
import random
import csv
import os.path
import yaml

from pathlib import Path
from tqdm import tqdm

creds = yaml.safe_load(Path(r'../credentials.yml').read_text())
USER_LOGIN = creds['user']['USER_LOGIN']
USER_PASSWORD = creds['user']['USER_PASSWORD']
SCROLL_PAUSE_TIME = 0.5
confs = yaml.safe_load(Path(r'../configuration.yml').read_text())
KEYWORDS = []
for title in confs['link_parsing']['titles']:
    for prof in confs['link_parsing']['profs']:
        KEYWORDS.append((title + ' ' + prof).strip().replace(' ', '%20'))
PAGE_NUM = confs['link_parsing']['page_num']


def get_time(base: int) -> int:
    """
    Returns randomized time shift, sometimes multiply shift by base.
    """
    factor = random.randint(1, 20)
    if factor == 1:
        result = base + base * random.randint(1, 10)
    else:
        result = base + random.randint(1, 10)
    return result


def session_init() -> None:
    """
    Initialize session.
    """
    caps = DesiredCapabilities().CHROME
    caps['pageLoadStrategy'] = 'eager'
    # noinspection PyGlobalUndefined
    global driver
    driver = webdriver.Chrome()


# noinspection PyBroadException
def log_in() -> None:
    """
    Login in.
    """
    try:
        driver.find_element(By.CLASS_NAME, 'global-nav__me-photo')
        return None
    except:
        driver.get("https://linkedin.com/uas/login")
        time.sleep(30)
        username = WebDriverWait(driver, timeout=30).until(lambda d: d.find_element(By.ID, "username"))
        username.send_keys(USER_LOGIN)
        time.sleep(get_time(5))
        pword = driver.find_element(By.ID, "password")
        pword.send_keys(USER_PASSWORD)
        time.sleep(get_time(5))
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(120)


def csv_write(data: list, path: str, header=None) -> None:
    """
    Write new line to csv file, if file doesn't exist - creates one with header.
    """
    if header is None:
        header = ['account_link', 'search_keywords']
    if not os.path.isfile(path):
        with open(path, 'a', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
    with open(path, 'a', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(data)


def scroll_page() -> None:
    """
    Scroll down till end of the page to make sure there is "Next" button.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


# noinspection PyBroadException
def parse_links(page_num: int = PAGE_NUM, path: str = Path(r'../data/01_raw/raw_links.csv'), keywords=None) -> None:
    """
    Search for keywords, navigate through pages and save links to path file.
    """
    if keywords is None:
        keywords = KEYWORDS
    for keyword in tqdm(keywords, desc='Keywords: '):
        driver.get(
            'https://www.linkedin.com/search/results/people/?keywords='
            + keyword
            + '=GLOBAL_SEARCH_HEADER&page=21&sid=QDs'
        )
        for _ in tqdm(range(page_num), desc='Pages: '):
            search_result_links = driver.find_elements(By.CSS_SELECTOR, "div.entity-result__item a.app-aware-link")
            for link in search_result_links:
                href = link.get_attribute("href")
                if 'linkedin.com/in' in href:
                    string = [href[:href.rfind('?miniProfileUrn')], keyword.replace('%20', ' ')]
                    csv_write(string, path)
            scroll_page()
            try:
                next_button = WebDriverWait(driver, timeout=30).until(
                    lambda d: d.find_element(By.CLASS_NAME, 'artdeco-pagination__button--next')
                )
                next_button.click()
                time.sleep(get_time(5))
            except:
                break
    driver.quit()


if __name__ == '__main__':
    session_init()
    log_in()
    parse_links()
    input('Press Enter to exit parser.')
