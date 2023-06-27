import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import time
import re
import datetime
import yaml

from pathlib import Path
from tqdm import tqdm
from link_parser import get_time, session_init, log_in, csv_write

creds = yaml.safe_load(Path(r'../credentials.yml').read_text())
USER_LOGIN = creds['user']['USER_LOGIN']
USER_PASSWORD = creds['user']['USER_PASSWORD']
confs = yaml.safe_load(Path(r'../configuration.yml').read_text())
POSTS_URL_SUFFIX = '/recent-activity/all/'


def scroll_page_gradually() -> None:
    """
    Scroll down gradually to make sure whole page is loaded and returns to "Show more" button.
    """
    html = driver.find_element(By.TAG_NAME, 'html')
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        while True:
            html.send_keys(Keys.END)
            time.sleep(get_time(0.5))
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 1500);")
        time.sleep(get_time(1))
        next_button = driver.find_element(By.CLASS_NAME, 'scaffold-finite-scroll__load-button')
        if next_button is None:
            return
        else:
            next_button.click()


def parse_personal_page(profile_url: str) -> list:
    """
    Parse for personal page info and return it.
    """
    driver.get(profile_url)
    time.sleep(get_time(5))
    src = driver.page_source
    soup = BeautifulSoup(src, "lxml")
    name = soup.find('div', {'class': 'pv-text-details__left-panel'}).find("h1").get_text().strip()
    title = soup.find('div', {'class': 'pv-text-details__left-panel'}).find("div", {'class': 'text-body-medium'})\
        .get_text().strip()
    works_at = soup.find('button', {'class': 'pv-text-details__right-panel-item-link'}).get_text().strip()
    intro = soup.find('div', {'class': 'pv-shared-text-with-see-more'}).get_text().strip()
    experience = (datetime.date.today().year
                  - int(min(re.findall('\d{4}', soup.find('ul', {'class': 'pvs-list'}).get_text()))))
    place = soup.find('span', {'class': 'text-body-small inline t-black--light break-words'}).get_text().strip()
    personal_info = [name, title, works_at, intro, experience, place]
    return personal_info


def parse_posts(profile_url: str) -> dict:
    """
    Parse profile posts page for post's text, reactions, reposts and comments.
    """
    driver.get(profile_url + POSTS_URL_SUFFIX)
    time.sleep(get_time(5))
    scroll_page_gradually()
    time.sleep(get_time(5))
    src = driver.page_source
    soup = BeautifulSoup(src, 'lxml')
    posts = soup.find_all('li', class_='profile-creator-shared-feed-update__container')
    posts_info = {}
    counter = 0
    for post_src in posts:
        post_text_div = post_src.find('div', {'class': 'feed-shared-update-v2__description-wrapper mr2'})
        if post_text_div is not None:
            post_text = post_text_div.find('span', {'dir': 'ltr'}).get_text().strip()
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
    return posts_info


def parse(path_from: str = Path(r'../data/02_intermediate/clean_links.csv'),
          path_to: str = Path(r'../data/01_raw/raw_posts.csv')) -> None:
    """
    Get information parsed from personal page, from posts and save it to file.
    """
    df = pd.read_csv(path_from)
    header = ['account_link', 'search_keywords',
              'posts_cnt', 'name', 'title', 'works_at', 'intro', 'experience', 'place',
              'post_text', 'reaction_cnt', 'comments_cnt', 'repost_cnt']
    for row in tqdm(df[:5].iterrows(), desc='Pages passed: '):
        personal_info = parse_personal_page(row[1]['account_link'])
        posts_info = parse_posts(row[1]['account_link'])
        posts_cnt = len(posts_info)
        for post in posts_info:
            data = [row[1]['account_link'], row[1]['search_keywords'], posts_cnt] + personal_info + posts_info[post]
            csv_write(data, path_to, header)


if __name__ == '__main__':
    session_init()
    log_in()
    parse()
    input('Enter anything to exit parser.')
