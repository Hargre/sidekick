import inspect
from functools import partial, wraps

from .bare_functions import identity, flip
from .placeholder import placeholder, _


def prop_delegate(name, default):
    "Delegate property to the _ attribute of an fn object."

    if callable(default):
        fget = lambda self: getattr(self._, name, default())
    else:
        fget = lambda self: getattr(self._, name, default)
    return property(fget) 


class fnMeta(type):
    "Metaclass for the fn type"
    
    def __rshift__(self, other):
        return fn(other)

    def __getitem__(self, other):
        print(other)
        if isinstance(other, tuple):
            func, *args = other
            return fn(func).partial(*args)
        return fn(other)

    def curried(cls, func):
        """
        Construct a curried fn function.
        """
        return cls(curry(func))


class fn(metaclass=fnMeta):
    """
    A function wrapper that enable functional programming superpowers.
    """

    def __init__(self, function):
        if isinstance(function, placeholder):
            function = function._
        self._ = function

    def __repr__(self):
        try:
            return 'fn(%s)' % self._.__name__
        except AttributeError:
            return 'fn(%r)' % self._

    def __call__(self, *args, **kwargs):
        return self._(*args, **kwargs)

    # Pipe operator
    def __ror__(self, other):
        return self._(other)

    # Function composition operators
    def __rrshift__(self, other):
        if isinstance(other, fn):
            other = other._
        function = self._
        return fn(lambda *args, **kw: function(other(*args, **kw)))

    def __rshift__(self, other):
        if isinstance(other, fn):
            other = other._
        function = self._
        return fn(lambda *args, **kw: other(function(*args, **kw)))

    __lshift__ = __rrshift__
    __rlshift__ = __rshift__

    # Partial application
    def __getitem__(self, item):
        if not isinstance(item, tuple):
            item = item,
        return self.partial(*item)
        
    # Make fn-functions behave nicely as methods
    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        else:
            return partial(self._, instance)
    
    # Function attributes
    __name__ = prop_delegate('__name__', 'lambda')
    __annotations__ = prop_delegate('__annotations__', dict)
    __closure__ = prop_delegate('__closure__', None)
    __code__ = prop_delegate('__code__', None)
    __defaults__ = prop_delegate('__defaults__', None)
    __globals__ = prop_delegate('__globals__', dict)
    __kwdefaults__ = prop_delegate('__kwdefaults__', None)
    __module__ = prop_delegate('__module__', '')
    __doc__ = prop_delegate('__doc__', None)

    # Public methods
    def partial(self, *args, **kwargs):
        """
        Return a fn-function with all given positional and keyword arguments 
        applied.
        """
        args_placeholder = \
            any(isinstance(x, placeholder) for x in args) 
        kwargs_placeholder = \
            any(isinstance(x, placeholder) for x in kwargs.values())

        # Simple partial application with no placeholders
        if not (args_placeholder or kwargs_placeholder):
            return fn(partial(self._, *args, **kwargs))
        
        elif not kwargs_placeholder:
            func = self._
            return fn(lambda x: \
                func(*((x if e is _ else e) for e in args), **kwargs)
            )

        elif not args_placeholder:
            func = self._
            return fn(lambda x: \
                func(
                    *args, 
                    **{k: (x if v is _ else v) for k, v in kwargs.items()}
                )
            )
        
        else:
            func = self._
            return fn(lambda x: \
                func(
                    *((x if e is _ else e) for e in args), 
                    **{k: (x if v is _ else v) for k, v in kwargs.items()}
                )
            )


def curry(func):
    """
    Return the curried version of a function.
    """

    spec = inspect.getfullargspec(func)
    if spec.varargs or spec.varkw or spec.kwonlyargs:
        raise TypeError('cannot curry a variadic function')
    
    def incomplete_factory(arity, used_args):
        return lambda *args: (
            func(*used_args, *args) 
            if len(used_args) + len(args) >= arity 
            else incomplete_factory(arity, used_args + args)
        )
    return incomplete_factory(len(spec.args), ())
