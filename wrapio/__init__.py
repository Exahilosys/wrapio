import collections
import functools
import weakref
import inspect
import asyncio

from . import waits
from . import helpers


__all__ = ('Handle', 'event', 'Track')


loading = {}


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
        loading[name] = value
        return value

    return helpers.register(apply, name)


events = weakref.WeakKeyDictionary()


class HandleMeta(type):

    def __new__(cls, name, bases, space, **kwargs):

        space = dict(space)

        store = {}

        for base in bases:
            try:
                others = events[base]
            except KeyError:
                continue
            store.update(others)

        store.update(loading)

        for (key, value) in store.items():
            try:
                other = space[key]
            except KeyError:
                continue
            if not other is value:
                continue
            del space[key]

        self = super().__new__(cls, name, bases, space, **kwargs)

        loading.clear()

        events[self] = store

        return self


def _noop(*args, **kwargs):

    pass


async def _anoop(*args, **kwargs):

    pass


class Handle(metaclass = HandleMeta):

    """
    Base class for those implementing the event protocol.

    :param bool sync:
        Used for creating tasks from the result of callbacks.
    :param bool aware:
        Whether to look into the last frame's local variables to find keys for
        creating a cached :func:`collections.namedtuple` for gathering dispatch
        values. Only use this if all events use a constant number of
        persistantly named values.

    The idea behind this is being able to make classes that handle specific
    operations on signal. First, create a class with this as its subclass.
    Then, use the :func:`event` module decorator to register methods as handles.
    Sending data to them can be done via :meth:`Handle.invoke` after
    instantiation.

    .. code-block::

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

    __slots__ = ('_callback', '_aware', '_async')

    def __init__(self, callback = None, aware = False, sync = True):

        self._callback = callback or (_noop if sync else _anoop)
        self._aware = {} if aware else None
        self._async = not sync

    def _dispatch(self, name, *values):

        if not self._aware is None:
            try:
                cls = self._aware[name]
            except KeyError:
                cls = self._aware[name] = helpers.subconverge(1, name, values)
            values = (cls(*values),)

        result = self._callback(name, *values)

        return result

    def invoke(self, name, *args, **kwargs):

        """
        Call the function that's supposed to handle the event.

        :param str name:
            The name of the event.

        Any other parameters used will be passed to the function call.
        """

        event = events[self.__class__][name]
        result = event(self, *args, **kwargs)

        if self._async:
            result = asyncio.create_task(result)

        return result


del HandleMeta


class Track:

    """
    Register callback functions against names.

    :param bool sync:
        Whether to use :mod:`threading` or :mod:`asyncio` for concurrency.
    :param bool parse:
        Whether to transform all incoming names into the same format.
    """

    __slots__ = ('_points', '_schedule', '_skip', '_async', '__weakref__')

    _last = None

    def __init__(self, sync = False, parse = True):

        self._points = collections.defaultdict(list)
        self._schedule = waits.Threading() if sync else waits.Asyncio()
        self._skip = not parse

    def _parse(self, name):

        if self._skip:

            return name

        return name.replace(' ', '_').lower()

    def call(self, func):

        """
        Decorator for registering callbacks against the name. Use like
        :func:`event`.
        """

        def apply(name, value):
            name = self._parse(name)
            callbacks = self._points[name]
            callbacks.append(value)
            return value

        return helpers.register(apply, func)

    def remove(self, func, name = None):

        """
        Remove the callback for the name.

        .. code-block:: py

            @track.call
            def hello():
                print('hi there')
            # ...
            track.remove(hello)
        """

        def apply(name, value):
            name = self._parse(name)
            callbacks = self._points[name]
            callbacks.remove(value)

        result = helpers.register(apply, name or func)

        if name:
            result(func) # execute the decorator, if exists

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
            name = self._parse(name)
            callbacks = self._points[name]
            def apply(func, last = None):
                callbacks.append(func)
                manage = functools.partial(callbacks.remove, func)
                event = self._schedule(manage, last)
                if not last:
                    self.__class__._last = staticmethod(func)
                return event
            return apply(value) if callable(value) else apply(self._last, value)

        return helpers.register(apply, name)

    def invoke(self, name, *args, **kwargs):

        """
        Call all registered functions against this name with the arguments.
        If ``sync`` was set to false, coroutines are gathered and scheduled as a
        future which is returned instead of a tuple of results.
        """

        name = self._parse(name)
        callbacks = self._points[name]

        result = tuple(callback(*args, **kwargs) for callback in callbacks)

        if isinstance(self._schedule, waits.Asyncio):
            future = asyncio.gather(*result)
            result = asyncio.ensure_future(future)

        return result
