import logging
import logging.handlers

from functools import wraps
import traceback
import re

from DrissionPage import ChromiumPage, ChromiumOptions
import pymysql


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


def get_keywords(db: pymysql.Connection) -> list[str]:
    with db.cursor() as cursor:
        cursor.execute("select keywords from reptile_keywords;")
        return [_[0] for _ in cursor.fetchall()]


def get_ex_keys(db: pymysql.Connection) -> list[str]:
    with db.cursor() as cursor:
        cursor.execute("select keywords from exclude_keywords;")
        return [_[0] for _ in cursor.fetchall()]


def get_last_step(db: pymysql.Connection, website_id) -> str:
    with db.cursor() as cursor:
        cursor.execute("SELECT last_step FROM reptile_time "
                       f"WHERE website_id = {website_id} "
                       "ORDER BY last_time DESC "
                       "LIMIT 1;")
        result = cursor.fetchone()
        return result[0] if result else ''


def get_site_info(db: pymysql.Connection):
    with db.cursor() as cursor:
        cursor.execute("SELECT id, website_name, website_timeline FROM reptile_website "
                       f"WHERE website_isUse = 1;")
        return cursor.fetchall()


def kw_matching(content: str, ex_keys, keywords) -> str:
    for ex_key in ex_keys:
        if ex_key in content:
            return ''
    ret = []
    for key in keywords:
        if key in content:
            ret.append(key)
    return ','.join(ret)


def get_zb_ask(content: str):
    idx = content.find('投标人资格')
    sub_str = content[idx - 3: idx]
    match = re.search(r'\b\d+(\.\d+)?\b', sub_str)
    if not match:
        return ''
    zb_num = match.group()

    if len(zb_num) == 1:
        nx_num = str(int(zb_num) + 1) + sub_str[match.end()]
    elif len(zb_num) == 2 and zb_num[0] == '0':
        nx_num = str(int(zb_num) + 1) + sub_str[match.end()]
    elif len(zb_num) == 3:
        nx_num = str(float(zb_num) + 0.1)
    else:
        raise Exception('非预期中的投标资格编号！')

    nx_idx = content[idx:].find(nx_num)
    return content[idx: idx + nx_idx]


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


def get_driver(port):
    co = ChromiumOptions().set_local_port(port)
    co.set_browser_path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    co.headless(True)
    co.no_imgs(True)

    driver = ChromiumPage(co)
    driver.set.blocked_urls('*.css*')
    return driver


logger = set_logger()
