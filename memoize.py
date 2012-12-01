import functools

__all__ = ['memoize', 'const_property']

class memoize(object):
    """
    A decorator that adds memoization to any method, thereby avoiding
    recomputation of the value.
    """
    __memos = {}
    class __nothing: pass

    def __init__(self, fn):
        self.fn = fn

    def __method(self, target, *args):
        """
        >>> class X(object):
        ...     @memoize
        ...     def f(self, x, y):
        ...         print x, y
        >>> a = X()
        >>> for x in range(3):
        ...     for y in range(3):
        ...         a.f(x,y)
        0 0
        0 1
        0 2
        1 0
        1 1
        1 2
        2 0
        2 1
        2 2
        >>> for x in range(3):
        ...     for y in range(3):
        ...         a.f(x,y)
        >>>
        """
        attrname = '_memoize__' + self.fn.__name__
        memos = target.__dict__.setdefault(attrname, {})
        if args in memos:
            return memos[args]
        memos[args] = result = self.fn(target, *args)
        return result

    def __call__(self, *args):
        """
        >>> @memoize
        ... def f(x, y):
        ...     print x, y
        ...
        >>> for x in range(3):
        ...     for y in range(3):
        ...         f(x,y)
        0 0
        0 1
        0 2
        1 0
        1 1
        1 2
        2 0
        2 1
        2 2
        >>> for x in range(3):
        ...     for y in range(3):
        ...         f(x,y)
        >>>
        """
        key = (self.fn,)+args
        v = self.__memos.get(key, self.__nothing)
        if v is self.__nothing:
            v = self.__memos[key] = self.fn(*args)
        return v

    def __get__(self, obj, objtype):
        # Support instance methods.
        return functools.partial(self.__method, obj)

def const_property(fn):
    """
    A decorator for lazily-computed, memoized, read-only properties.

    class X(object):
        @const_property
        def some_attribute_name():
            return compute_the_value();

    a = X()
    b = x.some_attribute_name # compute_the_value called here
    c = x.some_attribute_name # compute_the_value not called again
    """
    @property
    def wrapped(self):
        attrname = '_const_property__' + fn.__name__
        if not hasattr(self, attrname):
            setattr(self, attrname, fn(self))
        return getattr(self, attrname)

    return wrapped

if __name__ == '__main__':
    import doctest
    doctest.testmod()
