import inspect
import collections


__all__ = ()


def register(apply, name, check = callable):

    def wrapper(value):

        return apply(name, value)

    if not check(name):

        return wrapper

    (name, value) = (name.__name__, name)

    return wrapper(value)


def subconverge(level, name, values):

    stack = inspect.stack()

    items = stack[level + 1].frame.f_locals.items()

    space = dict(map(reversed, items))

    count = len(space)

    product = (space[value] for value in values)

    name = ''.join(name.title().replace(' ', ''))

    return collections.namedtuple(name, product)
