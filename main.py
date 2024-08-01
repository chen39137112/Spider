from threading import Thread

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
        self.keywords = self.get_keywords()
        self.ex_keys = self.get_ex_keys()
        self.websites = self.get_site_info()

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

    def run(self):
        threads = []

        for site in self.websites:
            t = Thread(target=self.crawling, args=(site,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.db.close()


if __name__ == '__main__':
    spider = Spider()
    spider.run()
