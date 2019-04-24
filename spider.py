import os

from common.base_crawler import Crawler
from asyncio import Queue
import asyncio
from config.config import *
import aiofiles
from decorators.decorators import decorator
from logger.log import storage

headers = {
    "host": "api.meizitu.net",
    "Referer": "https://app.mmzztt.com",
    "user-agent": "Mozilla/5.0 (Linux; Android 9; ALP-AL00 Build/HUAWEIALP-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/72.0.3626.121 Mobile Safari/537.36"
}
headers2 = {

}


class MZTAPP_Spider(Crawler):
    def __init__(self):
        self.q = Queue()
        self.q2 = Queue()

    @decorator()
    async def start(self):
        [self.q.put_nowait(
            f"https://api.meizitu.net/wp-json/wp/v2/comments?post={POST_ID}&per_page={PER_PAGE}&page={i}") for i in
            range(1, MAX_PAGE)]
        await self.init_session()
        tasks = [asyncio.Task(self.work()) for _ in range(CONCURRENCY_NUM)]
        await self.q.join()
        for i in tasks:
            i.cancel()
        # await asyncio.wait(tasks)
        # await self.close()

    async def work(self):
        try:
            while not self.q.empty():
                url = await self.q.get()
                await self.get_page(url)
                self.q.task_done()
        except asyncio.CancelledError:
            pass

    async def work2(self):
        while not self.q2.empty():
            dic = await self.q2.get()
            await self.get_img(dic)

    @decorator(False)
    async def get_img(self, dic):
        kwargs = {"headers": headers2}
        url = dic["img_src"]
        title = dic['date'].replace("-", "").replace(":", "")
        file_name = title[0:8]
        id = dic['id']
        if not os.path.exists(f"{FILE_PATH}/{IMAGE_TYPE}/{file_name}/{title}_{id}.jpg"):
            response = await self.get_session(url, kwargs)
            buff = response.source
            await self.save_img(buff, file_name, id)

    async def get_page(self, url):
        kwargs = {"headers": headers}
        response = await self.get_session(url, kwargs)
        j_data = response.source
        [self.q2.put_nowait(data) for data in j_data]
        tasks = [asyncio.ensure_future(self.work2()) for _ in range(len(j_data))]
        await asyncio.wait(tasks)

    async def save_img(self, buff, filename, index):
        file_path = f"{FILE_PATH}/{IMAGE_TYPE}/{filename}"
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        img_path = os.path.join(file_path, f"{index}.jpg")
        storage.info(f"正在保存:{img_path}")
        if os.path.exists(img_path):
            pass
        else:
            async with aiofiles.open(img_path, "wb") as fs:
                await fs.write(buff)


if __name__ == '__main__':
    m = MZTAPP_Spider()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(m.start())
    finally:
        loop.stop()
        loop.run_forever()
        loop.close()
