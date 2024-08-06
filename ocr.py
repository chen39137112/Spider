import time
import fitz
from paddleocr import PaddleOCR

from PIL import Image
import numpy as np


class MyPaddleOcr:
    def __init__(self):
        self.paddle = PaddleOCR(use_angle_cls=True, lang="ch")

    def pdf_to_images(self, file):
        # 打开PDF文件
        doc = fitz.open(file)
        # 遍历PDF的每一页
        for page_num in range(len(doc)):
            # 加载页面
            page = doc.load_page(page_num)
            # 获取页面的像素矩阵
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image_array = np.array(image)
            pix = None
            page = None
            yield image_array

        # 关闭PDF文件
        doc.close()

    def ocr(self, file):
        ret = []
        gen = self.pdf_to_images(file)
        for p in gen:
            result = self.paddle.ocr(p)
            for line in result[0]:
                ret.append(line[1][0] + '\n')
        return ret


if __name__ == '__main__':
    pdo = MyPaddleOcr()
    text = pdo.ocr('./tmp/巴基斯坦恰希玛核电站5号机组基坑工程监测和检测服务项目招标公告.pdf')
    pass
