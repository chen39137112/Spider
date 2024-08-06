from datetime import datetime
from datetime import timedelta

from ocr import MyPaddleOcr
from save import RecordMain, RecordContent, RecordAnnex, Saver
from utils import (logger,
                   trace_debug,
                   kw_matching,
                   get_zb_ask,
                   string_truncate,
                   download_annex_2_local)


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

    def check(self, ele):
        # 新标签页中打开ele的链接
        url = ele.ele('tag:a').attr('href')
        logger.info(f"中核:开始搜索{url}")
        tab = self.browser.new_tab(url)

        # 等待pdf加载完成
        for _ in range(3):
            ret = tab.wait.eles_loaded('.page', timeout=20)
            if ret:
                break
            tab.refresh()
        else:
            logger.warning(f"中核:加载超时-{url}")
            return

        pages = tab.eles('.page')
        texts = []
        title = ele.ele('tag:a').text
        dl_flag = False
        if len(pages[0].ele('.textLayer').children()) == 1:
            # 无text，下载pdf
            download = tab('#download').click.to_download('./tmp', f'{title}.pdf')
            download.wait()
            dl_flag = True
            pdo = MyPaddleOcr()
            texts = pdo.ocr(f'./tmp/{title}.pdf')
        else:
            # 获取text
            for page in pages:
                if not page.attr('data-loaded'):
                    page.scroll.to_see()
                    page.wait(0.5)
                if page.attr('data-loaded'):
                    texts.append(page.text)

        # 匹配关键字
        content = ''.join(texts)
        keywords = kw_matching(content, self.ex_keys, self.keywords)
        if not keywords:
            tab.close()
            return
        logger.info(f"中核:匹配到关键字：{keywords}")

        # 下载附件
        annex_path = download_annex_2_local(tab, self.id, title, dl_flag)
        # 格式化入库信息
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
    def run(self, count):
        logger.info(f"开始爬取中核集团({count})...")
        self.browser.get('https://www.cnncecp.com/xzbgg/index.jhtml')
        for i in range(3):
            ret = self.browser.wait.eles_loaded('.List1')
            if ret: break
        eles = self.browser.ele('.List1').child().children()

        bid_num = eles[0].ele('tag:a').attr('href')
        self.saver.bid_num = bid_num
        page = 2
        today = datetime.today()

        while True:
            for ele in eles:
                if today - datetime.strptime(ele.ele('.Right Gray').text, '%Y-%m-%d') > self.line:
                    logger.info("已到达时效日期，本次爬取结束")
                    break
                if ele.ele('tag:a').attr('href') == self.last_bid_num:
                    logger.info("已到达上次爬取处，本次爬取结束")
                    break
                self.check(ele)
            else:
                # 继续下一页
                logger.info(f'获取第{page}页')
                self.browser.get(self.url.format(page))
                ret = self.browser.wait.eles_loaded('.List1')
                if ret:
                    eles = self.browser.ele('.List1').child().children()
                    page += 1
                else:
                    logger.warning('翻页未响应，尝试重新获取本页')
                    eles = []
                continue
            break

        self.saver.save()
        self.browser.quit()
        logger.info("中核集团爬取结束")
        return True


if __name__ == '__main__':
    from utils import get_driver

    website_id = 1
    driver = get_driver(12346)
    last_bid_num = '-1'
    keywords = ["软件", "设计"]
    ex_keys = ['中标公告']
    espid = Cnncecp(website_id, driver, last_bid_num, keywords, ex_keys, 2)
    espid.run()
