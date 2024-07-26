from threading import Thread
from pathlib import Path

from DrissionPage import WebPage, ChromiumOptions

from cnncecp import Cnncecp
from espic import Espic
from utils import (get_driver,
                   get_keywords,
                   get_ex_keys,
                   get_last_step,
                   get_site_info,
                   connect_db)

method_tab = {
    "中核集团": Cnncecp,
    "中广核集团": '',
    "国家电投集团": Espic,
    "中国华能": '',
    "军队采购网": '',
}


def main():
    Path('./tmp').mkdir(parents=True, exist_ok=True)
    Path('./log').mkdir(parents=True, exist_ok=True)
    db = connect_db()
    keywords = get_keywords(db)
    ex_keys = get_ex_keys(db)
    websites = get_site_info(db)
    threads = []
    pages = []

    for site in websites:
        cls = method_tab[site[1]]
        website_id = site[0]
        page = get_driver(website_id + 12345)
        pages.append(page)
        last_bid_num = get_last_step(db, website_id)

        obj = cls(website_id, page, last_bid_num, keywords, ex_keys, site[2])
        t = Thread(target=obj.run)
        threads.append(t)
        t.start()

    # todo 捕获线程返回值，若为false需重试几次
    for t in threads:
        t.join()

    for page in pages:
        page.quit()
    db.close()


if __name__ == '__main__':
    main()
