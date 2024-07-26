import time
from datetime import datetime
from datetime import timedelta

from save import RecordMain, RecordContent, Saver
from utils import logger, trace_debug, kw_matching, get_zb_ask, string_truncate


class Cnncecp:
    def __init__(self, website_id, driver, last_bid_num, keywords: list[str], ex_keys: list[str],
                 timeline: int):
        self.id = website_id
        self.browser = driver
        self.last_bid_num = last_bid_num
        self.keywords = keywords
        self.ex_keys = ex_keys
        self.line = timedelta(days=timeline)
        self.saver = Saver(website_id)
        self.url = "https://www.cnncecp.com/xzbgg/index_{}.jhtml"

    @trace_debug
    def run(self):
        page = 1
        self.browser.get(self.url.format(page))

        time.sleep(30)


if __name__ == '__main__':
    from utils import get_driver

    website_id = 1
    driver = get_driver(10001)
    last_bid_num = '-1'
    keywords = ["软件", "设计"]
    ex_keys = ['中标公告']
    espid = Cnncecp(website_id, driver, last_bid_num, keywords, ex_keys, 2)
    espid.run()
