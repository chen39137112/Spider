# -*-coding:utf-8 -*-
import base64
import time
import functools
import numpy as np

from DrissionPage import WebPage
from DrissionPage.common import Actions
from PIL import ImageChops, PngImagePlugin, Image
from io import BytesIO

from utils import logger


class Crack(object):
    """
    解决三代极验滑块验证码
    """

    def __init__(self, driver: WebPage):
        self.browser = driver
        self.table = [0 if _ < 50 else 1 for _ in range(256)]
        self.width = 250

        self.browser.listen.start('https://ebid.espic.com.cn//resource/gdtNew/images/Pic')
        logger.info("开始监听滑块背景图片")

    def get_images(self):
        """
        获取验证码图片
        :return: 图片的location信息
        """
        canvas = self.browser.ele('#captcha').child('tag:canvas')
        bg = self.get_decode_image(canvas.run_js('return this.toDataURL("image/png")'))

        packet = self.browser.listen.wait()
        src = Image.open(BytesIO(packet.response.body))

        return bg, src

    def get_decode_image(self, location_list):
        """
        解码base64数据
        """
        _, img = location_list.split(",")
        img = base64.decodebytes(img.encode())
        new_im = Image.open(BytesIO(img))

        return new_im

    def compute_gap(self, img1, img2):
        """计算缺口偏移 这种方式成功率很高"""
        # 将图片修改为RGB模式
        img1 = img1.convert("RGB")
        img2 = img2.convert("RGB")

        if img1.size[0] > img2.size[0]:
            img1 = img1.resize(img2.size, Image.Resampling.BICUBIC)
        else:
            img2 = img2.resize(img1.size, Image.Resampling.BICUBIC)

        # 计算差值
        diff = ImageChops.difference(img1, img2)

        # 灰度图
        diff = diff.convert("L")

        # 二值化
        diff = diff.point(self.table, '1')
        # diff.save('./diff.png')

        left = 0

        for w in range(left, diff.size[0]):
            lis = []
            for h in range(diff.size[1]):
                if diff.load()[w, h] == 1:
                    lis.append(w)
                if len(lis) > 5:
                    return w

    def ease_out_quad(self, x):
        return 1 - (1 - x) * (1 - x)

    def ease_out_quart(self, x):
        return 1 - pow(1 - x, 4)

    def ease_out_expo(self, x):
        if x == 1:
            return 1
        else:
            return 1 - pow(2, -10 * x)

    def get_tracks_2(self, distance, seconds, ease_func):
        """
        根据轨迹离散分布生成的数学 生成  # 参考文档  https://www.jianshu.com/p/3f968958af5a
        成功率很高 90% 往上
        :param distance: 缺口位置
        :param seconds:  时间
        :param ease_func: 生成函数
        :return: 轨迹数组 步数越多成功率越高
        """
        distance += int(distance / self.width * 35)
        tracks = [0]
        offsets = [0]
        for t in np.arange(0.0, seconds, 0.1):
            ease = ease_func
            offset = round(ease(t / seconds) * distance)
            tracks.append(offset - offsets[-1])
            offsets.append(offset)
        tracks.extend([-2, -1, -1, -0])
        return tracks

    def get_track(self, distance):
        """
        根据物理学生成方式   极验不能用 成功率基本为0
        :param distance: 偏移量
        :return: 移动轨迹
        """
        distance += 20
        # 移动轨迹
        track = []
        # 当前位移
        current = 0
        # 减速阈值
        mid = distance * 3 / 5
        # 计算间隔
        t = 0.5
        # 初速度
        v = 0

        while current < distance:
            if current < mid:
                # 加速度为正2
                a = 2
            else:
                # 加速度为负3
                a = -3
            # 初速度v0
            v0 = v
            # 当前速度v = v0 + at
            v = v0 + a * t
            # 移动距离x = v0t + 1/2 * a * t^2
            move = v0 * t + 0.5 * a * (t ** 2)
            # 当前位移
            current += move
            # 加入轨迹
            track.append(round(move))
        track.extend([-3, -3, -2, -2, -2, -2, -2, -1, -1, -1, -1])
        return track

    def move_to_gap(self, track_x, track_y):
        """移动滑块到缺口处"""
        slider = self.browser.ele('.slider')
        action = Actions(self.browser)
        action.move_to(slider)
        action.hold()

        while track_x:
            x = track_x.pop(0)
            y = track_y.pop(0)
            action.move(offset_x=x, offset_y=y, duration=0)
            time.sleep(0.01)

        action.release()

    def crack(self, url):
        # 打开浏览器

        self.browser.get(url)
        ret = self.browser.wait.eles_loaded("#captcha", timeout=10)

        if ret:
            # 获取图片
            bg_img, fullbg_img = self.get_images()
            self.width = bg_img.size[0]
            # 获取缺口位置
            gap = self.compute_gap(fullbg_img, bg_img)
            logger.info(f'缺口位置{gap}')

            track_x = self.get_tracks_2(gap, 10, self.ease_out_quart)
            track_y = self.get_tracks_2(-10, 10, self.ease_out_quart)
            logger.info("滑动轨迹x:" + str(track_x))
            logger.info("滑动距离:" + str(functools.reduce(lambda x, y: x + y, track_x)))
            self.move_to_gap(track_x, track_y)

            ret = self.browser.wait.eles_loaded(".newslist", timeout=10)
            if ret:
                logger.info('验证成功!\n')
                return True
            else:
                logger.info('验证失败!\n')
                return False

        else:
            if self.browser.ele('.newslist'):
                logger.info("验证成功")
                return True
            return False

    def __del__(self):
        self.browser.listen.stop()
        logger.info("停止监听滑块背景图片")


if __name__ == '__main__':
    from utils import get_driver
    driver = get_driver()
    crack = Crack(driver)
    count = 0
    for i in range(20):
        if crack.crack():
            time.sleep(1)
            count += 1
    print(f"成功率：{count / 20 * 100}%")
