from __future__ import annotations

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
confs = yaml.safe_load(Path(r'../configuration.yml').read_text())
KEYWORDS = []
for title in confs['link_parsing']['titles']:
    for prof in confs['link_parsing']['profs']:
        KEYWORDS.append((title + ' ' + prof).strip().replace(' ', '%20'))
PAGE_PASS = confs['link_parsing']['page_pass']
INIT_PAGE = confs['link_parsing']['init_page']
TIME_BASE = confs['link_parsing']['time_base']


def get_time(base: int | float) -> int | float:
    """
    Returns randomized time shift, sometimes multiply shift by base to increase dispersion.
    """
    factor = random.randint(1, 20)
    if factor == 1:
        result = base + base * random.randint(1, 10)
    else:
        result = base + base * random.random() * 2
    return result


def session_init():
    """
    Initialize session.
    """
    caps = DesiredCapabilities().CHROME
    caps['pageLoadStrategy'] = 'eager'
    driver = webdriver.Chrome()
    return driver


def log_in(driver) -> None:
    """
    Login in.
    """
    try:
        driver.find_element(By.CLASS_NAME, 'global-nav__me-photo')
        return None
    except:
        driver.get("https://linkedin.com/uas/login")
        time.sleep(15)
        username = WebDriverWait(driver, timeout=30).until(lambda d: d.find_element(By.ID, "username"))
        username.send_keys(USER_LOGIN)
        time.sleep(get_time(TIME_BASE))
        pword = driver.find_element(By.ID, "password")
        pword.send_keys(USER_PASSWORD)
        time.sleep(get_time(TIME_BASE))
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(60)


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


def scroll_page(driver) -> None:
    """
    Scroll down till end of the page to make sure there is "Next" button.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(get_time(TIME_BASE / 10))
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


# noinspection PyBroadException
def parse_links(driver, init_page: int = INIT_PAGE, page_pass: int = PAGE_PASS,
                path: str = Path(r'../data/01_raw/raw_links.csv'), keywords=None) -> None:
    """
    Search for keywords, navigate through pages and save links to path file.
    """
    if keywords is None:
        keywords = KEYWORDS
    for keyword in tqdm(keywords, desc='Keywords passed: '):
        if init_page > 1:
            page_url = ''
        else:
            page_url = '&page=' + str(init_page)
        driver.get(
            'https://www.linkedin.com/search/results/people/?keywords={0}=GLOBAL_SEARCH_HEADER{1}&sid=QDs'.format(
                keyword, page_url)
        )
        for _ in tqdm(range(page_pass), desc='Pages passed: '):
            search_result_links = driver.find_elements(By.CSS_SELECTOR, "div.entity-result__item a.app-aware-link")
            for link in search_result_links:
                href = link.get_attribute("href")
                if 'linkedin.com/in' in href:
                    string = [href[:href.rfind('?miniProfileUrn')], keyword.replace('%20', ' ')]
                    csv_write(string, path)
            scroll_page(driver)
            try:
                next_button = WebDriverWait(driver, timeout=30).until(
                    lambda d: d.find_element(By.CLASS_NAME, 'artdeco-pagination__button--next')
                )
                next_button.click()
                time.sleep(get_time(TIME_BASE))
            except:
                break
    driver.quit()


if __name__ == '__main__':
    chr_driver = session_init()
    log_in(chr_driver)
    parse_links(chr_driver)
    input('Enter anything to exit parser.')
