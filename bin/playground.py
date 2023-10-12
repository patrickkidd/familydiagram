import threading
import sys
from pkdiagram.pyqt import *
from pkdiagram import Debug


qnam = QNetworkAccessManager()


class Request:

    def __init__(self, index, url):
        self.index = index
        self.url = url
        self.reply = None
        self.loop = QEventLoop()
        self.cond = threading.Condition()

    def wait():
        self.loop.exec_()

    def go(self):
        self.loop.exec_()
        status_code = self.reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)

    async def __aenter__(self):
        Debug('__aenter__')

        def onFinished():
            status_code = self.reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            Debug('status_code: ', status_code)
            self.cond.notify()
            Debug('status_code: ', status_code)
        request = QNetworkRequest(QUrl(self.url))
        self.reply = qnam.sendCustomRequest(request, 'GET')
        self.reply.connect(onFinished)
        Debug(f"{self.index} waiting...")
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        Debug('__aexit__', self.index, status_code)



# def main():
#     app = QApplication(sys.argv)
#     for i in range(3):
#         async with Request(i, 'http://google.com/') as request:
#             await request.go()
#             Debug(f"    WITH: {request.index}")
#     app.exec()



import contextlib
def test_basic():
    exit_count = 0

    @contextlib.asynccontextmanager
    async def ctx(v):
        nonlocal exit_count
        await asyncio.sleep(0)
        yield v
        await asyncio.sleep(0)
        exit_count += 1

    group = AsyncContextGroup([ctx(i) for i in range(3)])
    async with group as yielded_values:
        assert yielded_values == tuple(range(3))

    assert exit_count == 3 


test_basic()