import collections
import functools
import weakref

from . import waits
from . import helpers


__all__ = ('Handle', 'event', 'Track')


_prepare = {}


def event(name):

    """
    Register an event.

    .. note::

        Should only be used during :class:`Handle`'s creation.

    Can be used with explicit or implicit names:

    .. code-block::

        @event
        def this_will_be_the_name(*args, **kwags): # ...

        @event('with this name')
        def irrelevant_function_name(*args, **kwargs): # ...

    .. warning::

        The existance of ``name`` in signature does not mean an explicit
        argument is required.
    """

    def apply(name, value):

        _prepare[name] = value

        return value

    return helpers.register(apply, name)


_events = weakref.WeakKeyDictionary()


class HandleMeta(type):

    def __new__(cls, name, bases, space):

        space = dict(space)

        events = _prepare.copy()

        for (key, value) in events.items():

            try:

                other = space[key]

            except KeyError:

                continue

            if not other is value:

                continue

            del space[key]

        _prepare.clear()

        self = super().__new__(cls, name, bases, space)

        for base in bases:

            try:

                others = _events[base]

            except KeyError:

                continue

            events.update(others)

        _events[self] = events

        return self


async def _noop(*args, **kwargs):

    pass


class Handle(metaclass = HandleMeta):

    """
    Base class for those implementing the event protocol.

    :param asyncio.AbstractEventLoop loop:
        Used for creating tasks from the result of callbacks.

    The idea behind this is being able to make classes that handle specific
    operations on signal. First, create a class with this as its subclass.
    Then, use the :func:`event` module decorator to register methods as handles.
    Sending data to them can be done via :meth:`Handle.invoke` after
    instantiation.

    .. code-block:: python

        class Impl(Handle):

            def __init__(self, apply = None, **kwargs):
                super().__init__(**kwargs)
                self._apply = apply

            def _process(self, data):
                if self._apply:
                    data = self._apply(data)
                return data

            @event
            def receive(self, data):
                data = self._process(data)
                self._dispatch('received', data)

    .. warning::

        All methods decorated with :func:`event` will be deleted from the
        class' namespace.

    After creating handles, end users can utilize these classes like so:

    .. code-block:: python

        # ...

        handle = Impl(apply = str.upper, callback = print)

        while True:

            data = socket.receive()

            handle.invoke('receive', data) # will print('received', data)

    This section will be updated with a more comprehensive example when
    available.
    """

    __slots__ = ('_loop', '_dispatch')

    def __init__(self, callback = None, loop = None):

        self._loop = loop

        self._dispatch = callback or _noop

    def invoke(self, name, *args, **kwargs):

        """
        Call the function that's supposed to handle the event.

        :param str name:
            The name of the event.

        Any other parameters used will be passed to the function call.
        """

        event = _events[self.__class__]

        result = event(self, *args, **kwargs)

        if self._loop:

            result = self._loop.create_task(result)

        return result


del HandleMeta


class Track:

    """
    Register callback functions against names.

    :param asyncio.AbstractEventLoop loop:
        Signal the use of :py:mod:`asyncio` for concurrent operations.
    """

    __slots__ = ('_points', '_schedule', '_loop')

    def __init__(self, loop = None):

        self._points = collections.defaultdict(list)

        self._schedule = waits.asyncio(loop) if loop else waits.threading()

        self._loop = loop

    def call(self, name):

        """
        Decorator for registering callbacks against the name. Use like
        :func:`event`.
        """

        def apply(name, value):

            callbacks = self._points[name]

            callbacks.append(value)

            return value

        return helpers.register(apply, name)

    def wait(self, name):

        """
        Decorator for registering temporary callbacks against the name. Use like
        :func:`event`.

        .. warning::

            The final result is **not** a function; it's an
            :py:class:`asyncio.Event` or :py:class:`threading.Event` that should
            be set when appropriate; only then will each callback be forgotten.

        .. code-block:: python

            result = None

            @track.wait
            def on_receive(data):
                if not data.startswith('.'):
                    return
                nonlocal result
                result = data
                on_receive.set()

            on_receive.wait()
            print('done with', result)
        """

        def apply(name, value):

            callbacks = self._points[name]

            callbacks.append(value)

            manage = functools.partial(callbacks.remove, value)

            event = self._schedule(manage)

            return event

        return helpers.register(apply, name)

    def invoke(self, name, *args, **kwargs):

        """
        Call all register functions against this name with the arguments.
        If the ``loop`` param was used during instance creation, coroutines are
        gathered and scheduled as a future which is returned instead of a tuple
        of results.
        """

        callbacks = self._points[name]

        result = tuple(callback(*args, **kwargs) for callback in callbacks)

        if self._loop:

            values = map(helpers.condawait, result)

            future = asyncio.gather(*values, loop = self._loop)

            result = asyncio.ensure_future(future, loop = self._loop)

        return result
