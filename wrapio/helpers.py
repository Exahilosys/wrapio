

__all__ = ()


def register(apply, name, check = callable):

    def wrapper(value):

        return apply(name, value)

    if not check(name):

        return wrapper

    (name, value) = (name.__name__, name)

    return wrapper(value)
