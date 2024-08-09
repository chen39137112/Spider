from datetime import datetime
from datetime import timedelta
import logging
import logging.handlers
from pathlib import Path
from functools import wraps
import traceback
import re
import os
import shutil

from DrissionPage import ChromiumPage, ChromiumOptions
import pymysql

Path('./tmp').mkdir(parents=True, exist_ok=True)
Path('./log').mkdir(parents=True, exist_ok=True)
Path('./annex').mkdir(parents=True, exist_ok=True)


def set_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(process)d-%(threadName)s - '
                                  '%(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.handlers.TimedRotatingFileHandler('./log/spider.log', when='D', interval=1, backupCount=7,
                                                             encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def kw_matching(content: str, ex_keys, keywords) -> str:
    """
    使用正则匹配，防止关键词被换行符打断
    """
    ex_keys = ['(\n)?'.join(list(key)) for key in ex_keys]
    kw_patterns = ['(\n)?'.join(list(key)) for key in keywords]
    for ex_key in ex_keys:
        if re.search(ex_key, content):
            return ''

    ret = []
    for i, key in enumerate(kw_patterns):
        if re.search(key, content):
            ret.append(keywords[i])
    return ','.join(ret)


def get_zb_ask(content: str):
    idx = content.find('投标人资格')
    sub_str = content[idx - 3: idx]
    match = re.search(r'\b\d+(\.\d+)?\b', sub_str)
    if not match:
        return ''
    zb_num = match.group()
    suffix = '招标文件的获取' if len(sub_str) == match.end() else sub_str[match.end()]

    if len(zb_num) == 1:
        nx_num = str(int(zb_num) + 1) + suffix
    elif len(zb_num) == 2 and zb_num[0] == '0':
        nx_num = str(int(zb_num) + 1) + suffix
    elif len(zb_num) == 3:
        nx_num = str(float(zb_num) + 0.1)
    else:
        logger.warning('非预期中的投标资格编号！')
        return ''

    nx_idx = content[idx:].find(nx_num)
    if nx_idx == -1:
        nx_idx = content[idx:].find("招标文件的获取") - 2
    ret = content[idx: idx + nx_idx]
    i = 0
    while i < len(ret):
        s = ret[i]
        if s == '；' or s == '。' or s == '：':
            i += 1
            ret = ret[:i] + '\n' + ret[i:].strip()
        i += 1
    return ret


def string_truncate(s, max_bytes=65536, encoding='utf-8'):
    byte_s = s.encode(encoding)

    if len(byte_s) > max_bytes:
        truncated_byte_s = byte_s[:max_bytes - 50]
        truncated_s = truncated_byte_s.decode(encoding, 'ignore')
        return truncated_s + '...'
    else:
        return s


def trace_debug(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            logger.error(traceback.format_exc())
            return False

    return wrapper


def connect_db():
    return pymysql.connect(host="localhost",
                           port=3306,
                           user='root',
                           password='csh123',
                           database='zh_reptile',
                           charset='utf8mb3')


def save_annex_2_local(pages, website_id, title):
    today = datetime.today().strftime('%Y-%m-%d')
    parent = f'./annex/{today}/{website_id}/{title}'
    Path(parent).mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(pages):
        if not page.attr('data-loaded'):
            page.scroll.to_see()
            page.wait(0.5)
        if page.attr('data-loaded'):
            page.ele('.canvasWrapper').get_screenshot(path=parent, name=f'{i + 1}.png')
    return parent


def download_annex_2_local(tab, website_id, title, flag):
    today = datetime.today().strftime('%Y-%m-%d')
    parent = f'./annex/{today}/{website_id}/{title}'
    Path(parent).mkdir(parents=True, exist_ok=True)

    src_file = f'./tmp/{title}.pdf'
    dst_file = parent + '/附件.pdf'

    try:
        if flag:
            os.rename(src_file, dst_file)
        else:
            tab('#download').click.to_download(parent, '/附件.pdf')
    except FileExistsError:
        logger.info('文件已存在')
        os.remove(src_file)
    return parent


def clean_annex(date=30):
    """
    清理annex和tmp目录
    :param date: annex清理保存期限
    :return:
    """
    today = datetime.today()

    for d in os.listdir('./annex'):
        if today - datetime.strptime(d, '%Y-%m-%d') > timedelta(days=date):
            shutil.rmtree(d)

    try:
        shutil.rmtree('./tmp')
        os.makedirs('./tmp')
    except Exception as e:
        logger.error(f"清空目录时发生错误: {e}")


def get_driver(port):
    co = ChromiumOptions().set_local_port(port)
    if os.name != 'posix':
        browser_path = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
        useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36"
    else:
        browser_path = "/usr/bin/google-chrome"
        useragent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36"

    # co.headless(True)
    co.set_browser_path(browser_path)
    co.set_user_agent(user_agent=useragent)
    co.set_argument('--incognito')
    co.set_argument('--no-sandbox')
    # co.no_imgs(True)

    driver = ChromiumPage(co)
    # driver.set.blocked_urls('*.css*')
    return driver


logger = set_logger()
