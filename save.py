from dataclasses import dataclass, asdict
from datetime import datetime

from utils import connect_db, logger


@dataclass
class RecordMain:
    """
    要保存的内容：
    1、reptile_main
        `website_id` int(11) DEFAULT NULL COMMENT '关联网站表，关联reptile_website表',
        `reptile_keywords` varchar(5000) DEFAULT NULL COMMENT '关联关键词，多个关键词用逗号隔开',
        `title` varchar(1000) DEFAULT NULL COMMENT '标题',
        `reptile_time` datetime DEFAULT NULL COMMENT '爬虫时间',
        `website_time` datetime DEFAULT NULL COMMENT '原网站发布时间',
        `website_url` varchar(1000) DEFAULT NULL COMMENT '原网站链接',
    """
    website_id: int
    reptile_keywords: str
    title: str
    website_time: datetime
    website_url: str
    reptile_time: datetime = datetime.now()


@dataclass
class RecordContent:
    """
    要保存的内容：
    2、reptile_content
        `reptile_main_id` int(11) DEFAULT NULL COMMENT '爬虫主表ID，关联reptile_main表',
        `zb_ask` text COMMENT '招标资格要求',
        `reptile_content` text COMMENT '详细内容',
    """
    zb_ask: str
    reptile_content: str


class Saver:
    def __init__(self, website_id):
        self.db = connect_db()
        self.main: list[RecordMain] = []
        self.content: list[RecordContent] = []
        self.id = website_id
        self.bid_num = -1

    def add_main(self, record: RecordMain):
        self.main.append(record)

    def add_content(self, record: RecordContent):
        self.content.append(record)

    def insert(self, cursor, table, info: dict):
        cols = []
        vals = []
        for k, v in info.items():
            cols.append(k)
            vals.append(v)

        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['%s'] * len(cols))})"
        cursor.execute(sql, tuple(vals))
        return cursor.lastrowid

    def save(self):
        cursor = self.db.cursor()
        self.db.begin()
        try:
            for main_info, content in zip(self.main, self.content):
                main_dict = asdict(main_info)
                content_dict = asdict(content)

                main_id = self.insert(cursor, 'reptile_main', main_dict)
                content_dict['reptile_main_id'] = main_id
                self.insert(cursor, 'reptile_content', content_dict)

            self.insert(cursor, 'reptile_time', {'last_time': datetime.today(),
                                                 'website_id': self.id,
                                                 'last_step': self.bid_num})
            self.db.commit()
        except Exception as e:
            logger.error(e)
            self.db.rollback()
        finally:
            cursor.close()

    def __del__(self):
        self.db.close()


if __name__ == '__main__':
    saver = Saver(1)
    main_info = RecordMain(website_id=1,
                           reptile_keywords='设计,施工',
                           title="一个测试标题",
                           website_time=datetime.strptime("2024-04-05", '%Y-%m-%d'),
                           website_url="http::/www.test.com/",
                           )
    content_info = RecordContent(zb_ask="投标人资格123123", reptile_content="这是匹配到的内容123123", )
    saver.add_main(main_info)
    saver.add_content(content_info)

    main_info = RecordMain(website_id=2,
                           reptile_keywords='设计,开发',
                           title="一个测试标题",
                           website_time=datetime.strptime("2024-04-06", '%Y-%m-%d'),
                           website_url="http::/www.test.com/",
                           )
    content_info = RecordContent(zb_ask="投标人资格223123", reptile_content="这是匹配到的内容223123", )
    saver.add_main(main_info)
    saver.add_content(content_info)

    saver.save()
