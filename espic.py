import time
from datetime import datetime
from datetime import timedelta

from crack import Crack
from save import RecordMain, RecordContent, RecordAnnex, Saver
from utils import (logger,
                   trace_debug,
                   kw_matching,
                   get_zb_ask,
                   string_truncate,
                   save_annex_2_local)


class Espic:
    def __init__(self, website_id, driver, last_bid_num, keywords: list[str], ex_keys: list[str],
                 timeline: int):
        self.id = website_id
        self.browser = driver
        self.last_bid_num = last_bid_num
        self.keywords = keywords
        self.ex_keys = ex_keys
        self.line = timedelta(days=timeline)
        self.saver = Saver(website_id)
        self.url = 'https://ebid.espic.com.cn/newgdtcms//category/iframe.html?dates=300&categoryId=2' \
                   '&tenderMethod=01&tabName=招标公告&page={}&time=' + datetime.today().strftime("%Y-%m-%d")

    def crack(self, page):
        crack = Crack(self.browser)
        while True:
            for i in range(5):
                if crack.crack(self.url.format(page)):
                    logger.info(f"滑块破解成功，尝试{i + 1}次")
                    break
            else:
                logger.warning("滑块破解失败")
                # 若未找到502、503会直接抛出异常，方便定位
                text = self.browser.ele('@tag()=h1').text
                if text.find('502') != -1 or text.find('503') != -1:
                    logger.warning("服务器宕机502")
                    time.sleep(30)
                    continue
            break

    def check(self, ele):
        url = ele.child().property('href')
        logger.info(f"开始搜索{url}")
        tab = self.browser.new_tab(url)
        # 测试用
        # self.browser.get("https://ebid.espic.com.cn/sdny_bulletin/2024-07-22/599926.html")
        # iframe = self.browser.get_frame('#pdfContainer')

        iframe = tab.get_frame('#pdfContainer')
        tab.get(iframe.url)

        for _ in range(3):
            time.sleep(3)
            if tab.ele("#numPages").text != '/ 0':
                break
            tab.refresh()
        else:
            # todo 抛异常/跳过该条？
            raise Exception(f"frame页面加载失败，url:{url}")

        pages = tab.eles('.page')
        texts = []
        for page in pages:
            page.scroll.to_see()
            time.sleep(0.5)
            texts.append(page.text)

        content = ''.join(texts)
        keywords = kw_matching(content, self.ex_keys, self.keywords)
        if not keywords:
            tab.close()
            return

        # 匹配到了关键字
        logger.info(f"匹配到关键字：{keywords}")
        title = ele.child().property('title')
        # 缩小视图可保证截图完整
        tab.ele('#scaleSelect').select('50%')
        annex_path = save_annex_2_local(tab.eles('.page'), self.id, title)

        annex_info = RecordAnnex(annex_url=annex_path, annex_type=2)
        main_info = RecordMain(website_id=self.id,
                               reptile_keywords=keywords,
                               title=title,
                               website_time=datetime.strptime(ele.ele('.newsDate').text, '%Y-%m-%d'),
                               website_url=url
                               )
        content_info = RecordContent(zb_ask=get_zb_ask(content), reptile_content=string_truncate(content))

        self.saver.add_main(main_info)
        self.saver.add_content(content_info)
        self.saver.add_annex(annex_info)
        tab.close()

    @trace_debug
    def run(self):
        logger.info("开始爬取国家电投集团...")
        page = 1
        self.browser.get(self.url.format(page))
        # 尝试破解，若非预期原因失败，程序崩溃
        self.crack(page)
        eles = self.browser.ele(".newslist").children()

        bid_num = eles[0].ele('.col').child().text
        self.saver.bid_num = bid_num
        page += 1
        today = datetime.today()

        while True:
            for ele in eles:
                if today - datetime.strptime(ele.ele('.newsDate').text, '%Y-%m-%d') > self.line:
                    logger.info("已到达时效日期，本次爬取结束")
                    break
                if ele.ele('.col').child().text == self.last_bid_num:
                    logger.info("已到达上次爬取处，本次爬取结束")
                    break
                self.check(ele)
            else:
                # 继续下一页
                logger.info(f'获取第{page}页')
                self.browser.get(self.url.format(page))
                ret = self.browser.wait.eles_loaded(".newslist")
                if ret:
                    eles = self.browser.ele(".newslist").children()
                    page += 1
                else:
                    if self.browser.ele("#captcha"):
                        self.crack(page)
                        eles = self.browser.ele(".newslist").children()
                    else:
                        logger.warning('翻页未响应，尝试重新获取本页')
                        eles = []
                continue
            break

        self.saver.save()
        logger.info("国家电投集团爬取结束")
        return True


if __name__ == '__main__':
    from utils import get_driver

    website_id = 1
    driver = get_driver(10001)
    last_bid_num = '-1'
    keywords = ["软件", "设计"]
    ex_keys = ['中标公告']
    espid = Espic(website_id, driver, last_bid_num, keywords, ex_keys, 2)
    espid.run()
