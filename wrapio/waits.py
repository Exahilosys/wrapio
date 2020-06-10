import abc
import asyncio
import threading


__all__ = ()


class Wait(abc.ABC):

    __slots__ = ()

    _Event = None

    def __make(self, event):

        raise NotImplementedError()

    def __call__(self, manage, event = None):

        if not event:
            event = self._Event()

        self.__make(event)

        return event


class Asyncio(Wait):

    __slots__ = ()

    _Event = asyncio.Event

    def __make(self, event):

        coroutine = event.wait()
        task = loop.create_task(coroutine)

        callback = lambda task: manage()
        task.add_done_callback(callback)


class Threading(Wait):

    __slots__ = ()

    _Event = threading.Event

    def __make(self, event):

        def callback():
            event.wait()
            manage()

        thread = threading_.Thread(target = callback)
        thread.start()
