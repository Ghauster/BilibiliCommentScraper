from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import os
import csv
import re

def scroll_to_bottom(driver):
    SCROLL_PAUSE_TIME = 1
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            break

        last_height = new_height

def write_to_csv(video_id, index, level, parent_nickname, parent_user_id, nickname, user_id, content, time, likes):
    file_exists = os.path.isfile(f'{video_id}.csv')

    with open(f'{video_id}.csv', mode='a', encoding='utf-8', newline='') as csvfile:
        fieldnames = ['编号', '隶属关系', '被评论者昵称', '被评论者ID', '昵称', '用户ID', '评论内容', '发布时间',
                      '点赞数']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            '编号': index,
            '隶属关系': level,
            '被评论者昵称': parent_nickname,
            '被评论者ID': parent_user_id,
            '昵称': nickname,
            '用户ID': user_id,
            '评论内容': content,
            '发布时间': time,
            '点赞数': likes
        })


def extract_sub_reply(i, video_id, parent_nickname, parent_user_id, sub_all_reply_items):
    if i >= len(sub_all_reply_items):
        return

    sub_soup = BeautifulSoup(driver.page_source, "html.parser")
    sub_all_reply_items = sub_soup.find_all("div", class_="reply-item")

    # 提取二级评论数据
    sub_reply_list = sub_all_reply_items[i].find("div", class_="sub-reply-list")
    if sub_reply_list:
        for sub_reply_item in sub_reply_list.find_all("div", class_="sub-reply-item"):
            sub_nickname = sub_reply_item.find("div", class_="sub-user-name").text
            sub_user_id = sub_reply_item.find("div", class_="sub-reply-avatar")["data-user-id"]
            sub_content = sub_reply_item.find("span", class_="reply-content").text
            sub_time = sub_reply_item.find("span", class_="sub-reply-time").text
            try:
                sub_likes = sub_reply_item.find("span", class_="sub-reply-like").find("span").text
            except AttributeError:
                sub_likes = 0

            write_to_csv(video_id, index=i, level='二级评论', parent_nickname=parent_nickname,
                         parent_user_id=parent_user_id,
                         nickname=sub_nickname, user_id=sub_user_id, content=sub_content, time=sub_time,
                         likes=sub_likes)

driver = webdriver.Chrome(service=Service(executable_path=ChromeDriverManager().install()))
driver.get('https://space.bilibili.com/')
input("请登录，登录成功跳转后，按回车键继续...")

with open('video_list.txt', 'r') as f:
    video_urls = f.read().splitlines()

video_count = 0

for url in video_urls:
    video_count = video_count + 1
    i = 0
    video_id_search = re.search(r'https://www\.bilibili\.com/video/([^/?]+)', url)
    if video_id_search:
        video_id = video_id_search.group(1)
    else:
        print(f"无法从 URL 中提取 video_id: {url}")
        continue
    driver.get(url)
    # 在爬取评论之前滚动到页面底部
    scroll_to_bottom(driver)

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".reply-item")))

    soup = BeautifulSoup(driver.page_source, "html.parser")
    all_reply_items = soup.find_all("div", class_="reply-item")

    for i, reply_item in enumerate(all_reply_items):
        first_level_nickname = reply_item.find("div", class_="user-name").text
        first_level_user_id = reply_item.find("div", class_="root-reply-avatar")["data-user-id"]
        first_level_content = reply_item.find("span", class_="reply-content").text
        first_level_time = reply_item.find("span", class_="reply-time").text
        try:
            first_level_likes = reply_item.find("span", class_="reply-like").find("span").text
        except AttributeError:
            first_level_likes = 0

        write_to_csv(video_id, index=i, level='一级评论', parent_nickname='up主', parent_user_id='up主',
                     nickname=first_level_nickname, user_id=first_level_user_id, content=first_level_content,
                     time=first_level_time, likes=first_level_likes)

        view_more_buttons = driver.find_elements(By.XPATH, "//span[@class='view-more-btn']")

        clicked_view_more = False
        if len(view_more_buttons) > 0:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//span[@class='view-more-btn']")))
            driver.execute_script("arguments[0].scrollIntoView();", view_more_buttons[0])
            driver.execute_script("window.scrollBy(0, -300);")
            view_more_buttons[0].click()

            time.sleep(5)
            clicked_view_more = True

        extract_sub_reply(i, video_id, first_level_nickname, first_level_user_id, all_reply_items)

        if clicked_view_more:
            while True:
                next_buttons = driver.find_elements(By.CSS_SELECTOR, ".pagination-btn")
                found_next_button = False

                for button in next_buttons:
                    if "下一页" in button.text:
                        try:
                            button_xpath = f"//span[contains(text(), '下一页') and @class='{button.get_attribute('class')}']"
                            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
                            button_to_click = driver.find_element(By.XPATH, button_xpath)
                            button_to_click.click()
                            time.sleep(1)
                            extract_sub_reply(i, video_id, first_level_nickname, first_level_user_id,
                                              all_reply_items)
                            found_next_button = True
                            break
                        except ElementClickInterceptedException:
                            driver.execute_script("arguments[0].scrollIntoView();", button)
                            driver.execute_script("window.scrollBy(0, -300);")
                            button.click()

                            time.sleep(1)
                            extract_sub_reply(i, video_id, first_level_nickname, first_level_user_id,
                                              all_reply_items)
                            found_next_button = True
                            break

                if not found_next_button:
                    break

        print(f'第{video_count}个视频{video_id}-第{i+1}个一级评论已完成爬取')
        i = i + 1

    time.sleep(3)

driver.quit()