import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import time
import re
import datetime
import yaml
import random

from pathlib import Path
from tqdm import tqdm
from link_parser import get_time, session_init, log_in, csv_write

creds = yaml.safe_load(Path(r'../credentials.yml').read_text())
USER_LOGIN = creds['user']['USER_LOGIN']
USER_PASSWORD = creds['user']['USER_PASSWORD']
confs = yaml.safe_load(Path(r'../configuration.yml').read_text())
LIMIT_LOW = confs['post_parsing']['limit_low']
LIMIT_HIGH = confs['post_parsing']['limit_high']
TIME_BASE = confs['post_parsing']['time_base']
POSTS_URL_SUFFIX = 'recent-activity/all/'
RANDOM_URLS = ['https://www.linkedin.com/feed/', 'https://www.linkedin.com/mynetwork/',
               'https://www.linkedin.com/jobs/', 'https://www.linkedin.com/messaging/thread/new/',
               'https://www.linkedin.com/notifications/?filter=all', 'https://www.linkedin.com/post/new/']


def scroll_page_gradually(driver) -> None:
    """
    Scroll down gradually to make sure whole page is loaded and returns to "Show more" button.
    """
    html = driver.find_element(By.TAG_NAME, 'html')
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        while True:
            html.send_keys(Keys.END)
            time.sleep(get_time(TIME_BASE / 10))
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 1500);")
        time.sleep(get_time(TIME_BASE / 5))
        try:
            driver.find_element(By.CLASS_NAME, 'scaffold-finite-scroll__load-button').click()
        except:
            return


def parse_personal_page(driver, profile_url: str) -> list:
    """
    Parse for personal page info and return it.
    """
    driver.get(profile_url)
    time.sleep(get_time(TIME_BASE))
    src = driver.page_source
    soup = BeautifulSoup(src, "lxml")
    try:
        stop_word = soup.find(string=re.compile('Здесь будут отображаться'))
    except:
        stop_word = None
    try:
        name = soup.find('div', {'class': 'pv-text-details__left-panel'}).find("h1").get_text().strip()
    except:
        name = None
    try:
        title = soup.find('div', {'class': 'pv-text-details__left-panel'}
                          ).find("div", {'class': 'text-body-medium'}).get_text().strip()
    except:
        title = None
    works_at = soup.find('button', {'class': 'pv-text-details__right-panel-item-link'})
    if works_at is not None:
        works_at = works_at.get_text().strip()
    intro = soup.find('div', {'class': 'pv-shared-text-with-see-more'})
    if intro is not None:
        intro = intro.get_text().strip()
    try:
        experience = soup.select('div#experience')[0].find_next('ul')
        experience = datetime.date.today().year - int(min(re.findall('\d{4}', experience.get_text())))
    except:
        experience = None
    place = soup.find('span', {'class': 'text-body-small inline t-black--light break-words'})
    if place is not None:
        place = place.get_text().strip()
    personal_info = [stop_word, name, title, works_at, intro, experience, place]
    return personal_info


def parse_posts(driver, profile_url: str) -> dict:
    """
    Parse profile posts page for post's text, reactions, reposts and comments.
    :rtype: dict
    """
    current_url = driver.current_url
    driver.get(current_url + POSTS_URL_SUFFIX)
    time.sleep(get_time(TIME_BASE))
    scroll_page_gradually(driver)
    time.sleep(get_time(TIME_BASE))
    src = driver.page_source
    soup = BeautifulSoup(src, 'lxml')
    posts = soup.find_all('li', class_='profile-creator-shared-feed-update__container')
    posts_info = {}
    counter = 0
    for post_src in posts:
        post_text_div = post_src.find('div', {'class': 'feed-shared-update-v2__description-wrapper mr2'})
        if post_text_div is not None:
            try:
                post_text = post_text_div.find('span', {'dir': 'ltr'}).get_text().strip()
            except:
                post_text = None
        else:
            post_text = None
        reaction_cnt = post_src.find('li', {'class': 'social-details-social-counts__reactions'})
        if reaction_cnt is not None:
            reaction_cnt = int(max(re.findall('\d', reaction_cnt.get_text().strip())))
        comments_cnt = post_src.find('li', {'class': 'social-details-social-counts__comments'})
        if comments_cnt is not None:
            comments_cnt = int(max(re.findall('\d', comments_cnt.get_text().strip())))
        repost_cnt = post_src.find('li', {
            'class': 'social-details-social-counts__item social-details-social-counts__item--with-social-proof'})
        if repost_cnt is not None:
            repost_cnt = int(max(re.findall('\d', repost_cnt.get_text().strip())))
        posts_info[counter] = [post_text, reaction_cnt, comments_cnt, repost_cnt]
        counter += 1
    if len(posts_info) == 0:
        posts_info[0] = [None, None, None, None]
    return posts_info


def parse(driver,
          path_from: str = Path(r'../data/02_intermediate/clean_links.csv'),
          path_to: str = Path(r'../data/01_raw/raw_posts.csv'),
          limit_low: int = LIMIT_LOW, limit_high: int = LIMIT_HIGH) -> None:
    """
    Get information parsed from personal page, from posts and save it to file.
    """
    df = pd.read_csv(path_from)
    header = ['account_link', 'search_keywords',
              'name', 'title', 'works_at', 'intro', 'experience', 'place',
              'posts_cnt', 'post_text', 'reaction_cnt', 'comments_cnt', 'repost_cnt']
    for row in tqdm(df[limit_low:limit_high].iterrows(), desc='Pages passed: '):
        personal_info = parse_personal_page(driver, row[1]['account_link'])
        if personal_info[0] is None:
            personal_info = personal_info[1:]
            time.sleep(get_time(TIME_BASE))
            posts_info = parse_posts(driver, row[1]['account_link'])
        else:
            personal_info = personal_info[1:]
            posts_info = {0: [None, None, None, None]}
        posts_cnt = len(posts_info)
        if posts_cnt == 1 and (posts_info[0][0] == posts_info[0][1] == posts_info[0][2] == posts_info[0][3] is None):
            posts_cnt = 0
        for post in posts_info:
            data = [row[1]['account_link'], row[1]['search_keywords']]\
                   + personal_info + [posts_cnt] + posts_info[post]
            csv_write(data, path_to, header)
        factor = random.randint(1, 5)
        if factor == 1:
            url_index = random.randint(0, len(RANDOM_URLS) - 1)
            driver.get(RANDOM_URLS[url_index])
            time.sleep(get_time(TIME_BASE))


if __name__ == '__main__':
    chr_driver = session_init()
    log_in(chr_driver)
    parse(chr_driver)
    input('Enter anything to exit parser.')
