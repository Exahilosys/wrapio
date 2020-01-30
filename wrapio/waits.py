import asyncio as asyncio_
import threading as threading_


__all__ = ()


def asyncio(loop):

    def execute(manage, event = None):

        if not event:

            event = asyncio_.Event(loop = loop)

        coroutine = event.wait()

        task = loop.create_task(coroutine)

        callback = lambda task: manage()

        task.add_done_callback(callback)

        return event

    return execute


def threading():

    def execute(manage, event = None):

        if not event:

            event = threading_.Event()

        def callback():

            event.wait()

            manage()

        thread = threading_.Thread(target = callback)

        thread.start()

        return event

    return execute
