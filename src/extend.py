import functools
import inspect
from collections import ChainMap
from contextlib import suppress


def _get_first_external_stack_frame():
    for frameinfo in inspect.stack():
        if frameinfo.filename == __file__:
            continue
        return frameinfo.frame


def _is_in_scope(name, value):
    frame = _get_first_external_stack_frame()
    return ChainMap(frame.f_locals, frame.f_globals).get(name) == value


def monkey_extend(cls):
    def _decorator(f):
        setattr(cls, f.__name__, f)

    return _decorator


def scoped_extend(cls):
    def _decorator(f):
        def _getattr(obj, name):
            if name != f.__name__:
                raise AttributeError()

            if not _is_in_scope(f.__name__, f):
                raise AttributeError()

            return functools.partial(f, obj)

        cls.__getattr__ = _getattr
        return f

    return _decorator


def no_override_extend(cls):
    def _decorator(f):
        def _default(_obj, _name):
            raise AttributeError()

        original_getattr = getattr(cls, '__getattr__', _default)

        def _getattr(obj, name):
            with suppress(AttributeError):
                return original_getattr(obj, name)

            if name != f.__name__:
                raise AttributeError()

            if not _is_in_scope(f.__name__, f):
                raise AttributeError()

            return functools.partial(f, obj)

        cls.__getattr__ = _getattr
        return f

    return _decorator


def extension(scope_cls):
    cls = scope_cls.__base__

    def _default(_obj, _name):
        raise AttributeError()

    original_getattr = getattr(cls, '__getattr__', _default)

    def _getattr(obj, name):
        with suppress(AttributeError):
            return original_getattr(obj, name)

        if not hasattr(scope_cls, name):
            raise AttributeError()

        if not _is_in_scope(scope_cls.__name__, scope_cls):
            raise AttributeError()

        f = getattr(scope_cls, name)

        if isinstance(f, property):
            return f.__get__(obj)

        return functools.partial(f, obj)

    cls.__getattr__ = _getattr

    return scope_cls
