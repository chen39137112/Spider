from threading import Thread
from datetime import datetime, timedelta
import time

from cnncecp import Cnncecp
from espic import Espic
from utils import get_driver, connect_db

method_tab = {
    "中核集团": Cnncecp,
    "中广核集团": '',
    "国家电投集团": Espic,
    "中国华能": '',
    "军队采购网": '',
}


class Spider:
    def __init__(self):
        self.db = connect_db()


    def get_keywords(self) -> list[str]:
        with self.db.cursor() as cursor:
            cursor.execute("select keywords from reptile_keywords;")
            return [_[0] for _ in cursor.fetchall()]

    def get_ex_keys(self) -> list[str]:
        with self.db.cursor() as cursor:
            cursor.execute("select keywords from exclude_keywords;")
            return [_[0] for _ in cursor.fetchall()]

    def get_last_step(self, website_id) -> str:
        with self.db.cursor() as cursor:
            cursor.execute("SELECT last_step FROM reptile_time "
                           f"WHERE website_id = {website_id} "
                           "ORDER BY last_time DESC "
                           "LIMIT 1;")
            result = cursor.fetchone()
            return result[0] if result else ''

    def get_site_info(self):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT id, website_name, website_timeline FROM reptile_website "
                           f"WHERE website_isUse = 1;")
            return cursor.fetchall()

    def crawling(self, site_info):
        cls = method_tab[site_info[1]]
        website_id = site_info[0]
        page = get_driver(website_id + 12345)
        last_bid_num = self.get_last_step(website_id)

        obj = cls(website_id, page, last_bid_num, self.keywords, self.ex_keys, site_info[2])
        for i in range(3):
            if obj.run(i):
                break
        page.quit()

    def waiting(self):
        with self.db.cursor() as cursor:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            now = datetime.now()
            seconds = (now - today_start).total_seconds()

            cursor.execute("SELECT timeSwitch FROM reptile_timeswitch ORDER BY timeSwitch")
            times = [_[0].total_seconds() for _ in cursor.fetchall()]
            # 防止有0点导致无法触发
            if times[0] == 0:
                times.pop(0)
                times.append(timedelta(hours=24).total_seconds())
            times = [t - seconds for t in times]

            t = times.pop()
            while t > 0:
                if times[-1] > 0:
                    t = times.pop()
                else:
                    break

            if t < 0 or t > 60:
                time.sleep(10)
                return False
            if t <= 60:
                time.sleep(t)
                return True

    def run(self):
        while True:
            if not self.waiting():
                continue
            self.keywords = self.get_keywords()
            self.ex_keys = self.get_ex_keys()
            self.websites = self.get_site_info()
            threads = []

            for site in self.websites:
                t = Thread(target=self.crawling, args=(site,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()


if __name__ == '__main__':
    spider = Spider()
    spider.run()
