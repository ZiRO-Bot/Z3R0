import threading
import time


class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.stopEvent = threading.Event()
        thread = threading.Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self):
        nextTime = time.time() + self.interval
        while not self.stopEvent.wait(nextTime - time.time()):
            nextTime += self.interval
            self.action()

    def cancel(self):
        self.stopEvent.set()


class setTimeout:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.stopEvent = threading.Event()
        thread = threading.Thread(target=self.__setTimeout)
        thread.start()

    def __setTimeout(self):
        nextTime = time.time() + self.interval
        while not self.stopEvent.wait(nextTime - time.time()):
            nextTime += self.interval
            self.action()
            self.stopEvent.set()


# usage example:
## --- start action every 0.6s
# inter=setInterval(0.6,action)
# print('just after setInterval -> time : {:.1f}s'.format(time.time()-StartTime))

## --- will stop interval in 5s
# t=threading.Timer(5,inter.cancel)
# t.start()
