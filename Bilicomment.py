from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchWindowException
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pickle
import time
import os
import csv
import re
import json
import sys
import tempfile
import shutil

def write_error_log(message):
    with open("video_errorlist.txt", "a") as file:
        file.write(message + "\n")

def save_progress(progress):
    max_retries = 50
    retries = 0

    while retries < max_retries:
        try:
            with open("progress.txt", "w", encoding='utf-8') as f:
                json.dump(progress, f)
            break  # 如果成功保存，跳出循环
        except PermissionError as e:
            retries += 1
            print(f"进度存档时，遇到权限错误Permission denied，文件可能被占用或无写入权限: {e}")
            print(f"等待10s后重试，将会重试50次... (尝试 {retries}/{max_retries})")
            time.sleep(10)  # 等待10秒后重试
    else:
        print("进度存档时遇到权限错误，且已达到最大重试次数50次，退出程序")
        sys.exit(1)

def save_cookies(driver, cookies_file):
    with open(cookies_file, 'wb') as f:
        pickle.dump(driver.get_cookies(), f)

def load_cookies(driver, cookies_file):
    if os.path.exists(cookies_file):
        with open(cookies_file, 'rb') as f:
            cookies = pickle.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
        return True
    return False

def manual_login(driver, cookies_file):
    input("请登录，登录成功跳转后，按回车键继续...")
    save_cookies(driver, cookies_file)  # 登录后保存cookie到本地
    print("程序正在继续运行")

def check_page_status(driver):
    try:
        driver.execute_script('javascript:void(0);')
        return True
    except Exception as e:
        print(f"检测页面状态时出错，尝试刷新页面重新加载: {e}")
        driver.refresh()
        time.sleep(5)
        return False

def click_view_more(driver, view_more_button, i):
    success = False
    while not success:
        try:
            try:
                driver.execute_script("arguments[0].scrollIntoView();", view_more_button)
                driver.execute_script("window.scrollBy(0, -100);")
                view_more_button.click()
            except Exception:
                driver.execute_script("window.scrollBy(0, 300);")
                view_more_button.click()
            success = True
        except Exception as e:
            print(f"点击查看全部按钮时发生错误: {e}")
            if not check_page_status(driver):
                try:
                    scroll_to_bottom(driver)
                    view_more_buttons = driver.find_elements(By.XPATH, f".//div[@class='reply-item'][{i+1}]//span[@class='view-more-btn']")
                    WebDriverWait(driver, 30).until(
                        EC.element_to_be_clickable((By.XPATH, ".//span[@class='view-more-btn']")))
                    driver.execute_script("arguments[0].scrollIntoView();", view_more_buttons[0])
                    driver.execute_script("window.scrollBy(0, -100);")

                except Exception as e:
                    print(f"点击查看全部按钮时发生错误 - 刷新重试时出错{e}...")
                    raise

def click_next_page(driver, next_page_button, i, progress):
    try:
        try:
            driver.execute_script("arguments[0].scrollIntoView();", next_page_button)
            driver.execute_script("window.scrollBy(0, -100);")
            next_page_button.click()
        except Exception:
            driver.execute_script("window.scrollBy(0, 300);")
            next_page_button.click()
    except Exception as e:
        print(f"点击下一页按钮时发生错误: {e}")
        if not check_page_status(driver):
            try:
                scroll_to_bottom(driver)
                view_more_buttons = driver.find_elements(By.XPATH,
                                                         f".//div[@class='reply-item'][{i + 1}]//span[@class='view-more-btn']")
                WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@class='view-more-btn']")))
                driver.execute_script("arguments[0].scrollIntoView();", view_more_buttons[0])
                driver.execute_script("window.scrollBy(0, -100);")
                view_more_buttons[0].click()
                time.sleep(2)
                navigate_to_sub_comment_page(i, progress, driver)

            except Exception as e:
                print(f"点击查看全部按钮时发生错误 - 刷新重试时出错{e}...")
                raise

def close_mini_player(driver):
    try:
        close_button = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//div[@title="点击关闭迷你播放器"]'))
        )
        close_button.click()
    except Exception as e:
        print(f"[这不影响程序正常运行，可能悬浮小窗已被关闭（加这段只是因为悬浮小窗可能遮挡按钮，把浏览器拉宽可以避免按钮被遮挡）]未找到关闭按钮或无法关闭悬浮小窗: {e}")

def restart_browser(driver):
    driver.quit()
    shutil.rmtree(temp_dir)
    main()

def check_next_page_button(driver):
    next_buttons = driver.find_elements(By.CSS_SELECTOR, ".pagination-btn")
    for button in next_buttons:
        if "下一页" in button.text:
            return True
    return False

def navigate_to_sub_comment_page(i, progress, driver):
    current_page = 1
    target_page = progress["sub_page"]
    while current_page <= target_page:
        print(f'在存档中发现上次二级评论第{target_page}页已完成爬取，正在导航至上次爬取的二级评论页码断点')
        if not check_next_page_button(driver):
            break  # 没有下一页按钮时跳出循环
        next_buttons = driver.find_elements(By.CSS_SELECTOR, ".pagination-btn")
        for button in next_buttons:
            if "下一页" in button.text:
                button_xpath = f"//span[contains(text(), '下一页') and @class='{button.get_attribute('class')}']"
                WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
                try:
                    click_next_page(driver, button, i, progress)
                    time.sleep(2)
                    print(f'当前所在页码 / 上次二级评论页码：{current_page}/{target_page}')
                    current_page += 1
                    break
                except ElementClickInterceptedException:
                    print("下一页按钮 is not clickable, skipping...")

def scroll_to_bottom(driver):
    global mini_flag
    SCROLL_PAUSE_TIME = 4
    # B站每向下滚动一次，会加载20个一级评论。
    # 滚动次数过多，加载的数据过大，网页可能会因内存占用过大而崩溃。
    # 这里设置滚动次数为45次，最多收集到920条一级评论
    # 视频评论数 = 一级评论数 + 二级评论数，且存在虚标情况。经测试，滚动次数设为45次时，已完整爬取标称评论数为7443条的视频评论，共爬取到3581条评论。
    MAX_SCROLL_COUNT = 45
    scroll_count = 0

    try:
        last_height = driver.execute_script("return document.body.scrollHeight")
    except NoSuchWindowException:
        print("浏览器意外关闭...")
        raise

    while scroll_count < MAX_SCROLL_COUNT:
        try:
            driver.execute_script('javascript:void(0);')
        except Exception as e:
            print(f"检测页面状态时出错，尝试重新加载: {e}")
            driver.refresh()
            time.sleep(5)
            scroll_to_bottom(driver)
            time.sleep(SCROLL_PAUSE_TIME)
            raise

        try:
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            if mini_flag:
                close_mini_player(driver)
                mini_flag = False
        except NoSuchWindowException:
            print("关闭小窗时，浏览器意外关闭...")
            raise

        time.sleep(SCROLL_PAUSE_TIME)
        try:
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
        except NoSuchWindowException:
            print("页面向下滚动时，浏览器意外关闭...")
            raise

        if new_height == last_height:
            break

        last_height = new_height
        scroll_count += 1
        print(f'下滑滚动第{scroll_count}次 / 最大滚动{MAX_SCROLL_COUNT}次')

def write_to_csv(video_id, index, level, parent_nickname, parent_user_id, nickname, user_id, content, time, likes):
    file_exists = os.path.isfile(f'{video_id}.csv')
    max_retries = 50
    retries = 0

    while retries < max_retries:
        try:
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
            break  # 如果成功写入，跳出循环
        except PermissionError as e:
            retries += 1
            print(f"将爬取到的数据写入csv时，遇到权限错误Permission denied，文件可能被占用或无写入权限: {e}")
            print(f"等待10s后重试，将会重试50次... (尝试 {retries}/{max_retries})")
            time.sleep(10)  # 等待10秒后重试
    else:
        print("将爬取到的数据写入csv时遇到权限错误，且已达到最大重试次数50次，退出程序")
        sys.exit(1)

def extract_sub_reply(video_id, progress, first_level_nickname, first_level_user_id, driver):

    i = progress["first_comment_index"]

    sub_soup = BeautifulSoup(driver.page_source, "html.parser")
    sub_all_reply_items = sub_soup.find_all("div", class_="reply-item")

    if i >= len(sub_all_reply_items):
        print(str(f'翻页爬取二级评论时获得的一级评论数与实际一级评论数不符，视频{video_id}可能存在异常'))
        return

    # 提取二级评论数据
    sub_reply_list = sub_all_reply_items[i].find("div", class_="sub-reply-list")
    if sub_reply_list:
        for sub_reply_item in sub_reply_list.find_all("div", class_="sub-reply-item"):
            try:
                sub_reply_nickname = sub_reply_item.find("div", class_="sub-user-name").text
                sub_reply_user_id = sub_reply_item.find("div", class_="sub-reply-avatar")["data-user-id"]
                sub_reply_text = sub_reply_item.find("span", class_="reply-content").text
                sub_reply_time = sub_reply_item.find("span", class_="sub-reply-time").text
                try:
                    sub_reply_likes = sub_reply_item.find("span", class_="sub-reply-like").find("span").text
                except AttributeError:
                    sub_reply_likes = 0

                write_to_csv(video_id, index=i, level='二级评论', parent_nickname=first_level_nickname,
                             parent_user_id=first_level_user_id,
                             nickname=sub_reply_nickname, user_id=sub_reply_user_id, content=sub_reply_text, time=sub_reply_time,
                             likes=sub_reply_likes)

            except NoSuchElementException:
                print("Error extracting sub-reply element, skipping...")

        progress['sub_page'] += 1
        save_progress(progress)

def main():
    global temp_dir
    # 代码文件所在的文件夹内创建一个新的文件夹，作为缓存目录。如果想自行设定目录，请修改下面代码
    current_folder = os.path.dirname(os.path.abspath(__file__))
    temp_dir = tempfile.mkdtemp(dir=current_folder)

    # 首次登录获取cookie文件
    cookies_file = 'cookies.pkl'
    print("测试cookies文件是否已获取。若无，请在弹出的窗口中登录b站账号，登录完成后，窗口将关闭；若有，窗口会立即关闭")
    driver = webdriver.Chrome(service=Service(executable_path=ChromeDriverManager().install()))
    driver.get('https://space.bilibili.com/')
    if not load_cookies(driver, cookies_file):
        manual_login(driver, cookies_file)
    driver.quit()

    # 设置Chrome浏览器参数
    chrome_options = Options()
    # 将Chrome的缓存目录设置为刚刚创建的临时目录
    chrome_options.add_argument(f'--user-data-dir={temp_dir}')
    chrome_options.add_argument('--disable-plugins-discovery')
    chrome_options.add_argument('--mute-audio')
    # 开启无头模式，禁用视频、音频、图片加载，开启无痕模式，减少内存占用
    chrome_options.add_argument('--headless')   # 开启无头模式以节省内存占用，较低版本的浏览器可能不支持这一功能
    chrome_options.add_argument("--disable-plugins-discovery")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    chrome_options.add_argument("--incognito")
    # 禁用GPU加速，避免浏览器崩溃
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(service=Service(executable_path=ChromeDriverManager().install()), options=chrome_options)
    driver.get('https://space.bilibili.com/')
    load_cookies(driver, cookies_file)

    if os.path.exists("progress.txt"):
        with open("progress.txt", "r", encoding='utf-8') as f:
            progress = json.load(f)
    else:
        progress = {"video_count": 0, "first_comment_index": 0, "sub_page": 0, "write_parent": 0}

    with open('video_list.txt', 'r') as f:
        video_urls = f.read().splitlines()

    # 计算需要跳过的视频数量
    skip_count = progress["video_count"]
    global mini_flag
    mini_flag = True

    for url in video_urls:
        try:
            # 如果需要跳过此视频，减少跳过计数并继续循环
            if skip_count > 0:
                skip_count -= 1
                continue

            video_id_search = re.search(r'https://www\.bilibili\.com/video/([^/?]+)', url)
            if video_id_search:
                video_id = video_id_search.group(1)
                print(f'开始爬取第{progress["video_count"]+1}个视频{video_id}：先会不断向下滚动至页面最底部，以加载全部页面。对于超大评论量的视频，这一步会相当花时间，请耐心等待')
            else:
                error_message = f'第{progress["video_count"] + 1}个视频被跳过：无法从 URL {url}中提取 video_id'
                print(error_message)
                write_error_log(error_message)
                progress["video_count"] += 1
                continue

            driver.get(url)

            # 在爬取评论之前滚动到页面底部
            scroll_to_bottom(driver)

            try:
                WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".reply-item")))
            except TimeoutException:
                error_message = f'第{progress["video_count"] + 1}个视频被跳过：ID {video_id} URL {url}没有找到评论或等了30秒还没加载出来'
                print(error_message)
                write_error_log(error_message)
                progress["video_count"] += 1
                continue

            soup = BeautifulSoup(driver.page_source, "html.parser")
            all_reply_items = soup.find_all("div", class_="reply-item")

            for i, reply_item in enumerate(all_reply_items):

                if(i < progress["first_comment_index"]):
                    continue

                first_level_nickname_element = reply_item.find("div", class_="user-name")
                first_level_nickname = first_level_nickname_element.text if first_level_nickname_element is not None else ''

                first_level_user_id_element = reply_item.find("div", class_="root-reply-avatar")
                first_level_user_id = first_level_user_id_element[
                    "data-user-id"] if first_level_user_id_element is not None else ''

                first_level_content_element = reply_item.find("span", class_="reply-content")
                first_level_content = first_level_content_element.text if first_level_content_element is not None else ''

                first_level_time_element = reply_item.find("span", class_="reply-time")
                first_level_time = first_level_time_element.text if first_level_time_element is not None else ''

                try:
                    first_level_likes = reply_item.find("span", class_="reply-like").find("span").text
                except AttributeError:
                    first_level_likes = 0

                if (progress["write_parent"] == 0):
                    write_to_csv(video_id, index=i, level='一级评论', parent_nickname='up主', parent_user_id='up主',
                                 nickname=first_level_nickname, user_id=first_level_user_id, content=first_level_content,
                                 time=first_level_time, likes=first_level_likes)
                    progress["write_parent"] = 1
                    print(
                        f'第{progress["video_count"] + 1}个视频{video_id}-第{progress["first_comment_index"] + 1}个一级评论已写入csv。正在查看这个一级评论有没有二级评论')

                view_more_buttons = driver.find_elements(By.XPATH, f".//div[@class='reply-item'][{i+1}]//span[@class='view-more-btn']")

                clicked_view_more = False
                if len(view_more_buttons) > 0:
                    WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, "//span[@class='view-more-btn']")))
                    try:
                        click_view_more(driver, view_more_buttons[0], i)
                        time.sleep(2)
                        clicked_view_more = True
                        navigate_to_sub_comment_page(i, progress, driver)
                    except ElementClickInterceptedException:
                        print("查看全部 button is not clickable, skipping...")

                if reply_item.find("div", class_="sub-reply-list"):
                    extract_sub_reply(video_id, progress, first_level_nickname, first_level_user_id, driver)

                if clicked_view_more:
                    # 可以把max_sub_pages更改为您希望设置的最大二级评论页码数。
                    # 如果想无限制，请设为max_sub_pages = None。
                    # 设定一个上限有利于减少内存占用，避免页面崩溃。建议设为150。
                    max_sub_pages = 150
                    current_sub_page = progress["sub_page"]

                    while max_sub_pages is None or current_sub_page < max_sub_pages:
                        next_buttons = driver.find_elements(By.CSS_SELECTOR, ".pagination-btn")
                        found_next_button = False

                        for button in next_buttons:
                            if "下一页" in button.text:
                                button_xpath = f"//span[contains(text(), '下一页') and @class='{button.get_attribute('class')}']"
                                WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
                                try:
                                    click_next_page(driver, button, i, progress)
                                    time.sleep(2)
                                    extract_sub_reply(video_id, progress, first_level_nickname, first_level_user_id,
                                                      driver)
                                    print(f'发现多页二级评论，正在翻页：二级评论已爬取到第{progress["sub_page"]}页')
                                    found_next_button = True
                                    current_sub_page += 1
                                    break
                                except ElementClickInterceptedException:
                                    print("下一页按钮 is not clickable, skipping...")

                        if not found_next_button:
                            break

                print(f'第{progress["video_count"]+1}个视频{video_id}-第{progress["first_comment_index"]+1}个一级评论下的全部内容已完成爬取')

                progress["first_comment_index"] += 1
                progress["write_parent"] = 0
                progress["sub_page"] = 0
                save_progress(progress)

            progress["video_count"] += 1
            progress["first_comment_index"] = 0
            save_progress(progress)

        except WebDriverException as e:
            print(f"可能网页崩溃或网络连接中断，正在尝试重新启动浏览器: {e}")
            restart_browser(driver)

        except Exception as e:
            print(f"[若这条报错反复发生，请终止程序并检查]发生其他未知异常，尝试重新启动浏览器: {e}")
            restart_browser(driver)

    driver.quit()

if __name__ == "__main__":
    main()
