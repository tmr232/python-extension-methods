# Snake Eyes - Extension Methods

Today we set out to implement a feature I saw and liked in Kotlin - [Extension Methods].

You can follow along with working code samples [here][repl], or get the code [here][github]

Extension methods are a nice piece of syntactic-sugar that allow you to define free-functions
and call them like instance methods. In Kotlin, it looks something like this:

```kotlin
fun Square.draw() {
    drawSquare(this)
}

// ...

val square = getSquare()
square.draw()
```

Now, since they are free, static functions, they follow the same rules. They are
not part of the class, nor have access to private members. And they can only be
called in a scope where they are visible. Adding them in your code does not affect
other code. Additionally, true member functions, if they exist, take precedence over
extension methods (this is especially important with generic extension methods).

In our code today, we'll try to mimic the features of extension methods as closely
as possible. We'll use the following syntax:

```python
@extend(Square)
def draw(square):
    draw_square(square)
``` 

For extension methods, and the following implementation of `Square` in our code throughout:

```python
from dataclasses import dataclass

@dataclass
class Square:
    length: int
```

## Monkey Patching 🙈

Python is a very dynamic language. Among other things, it allows us to change the attributes
of (non-builtin) types at run-time. This means that we can extend our `Square` class
by adding a `draw` method to it at run-time.

```python
Square.draw = draw_square
``` 

We're now free to call `square.draw()`. Before we discuss the draw-backs, let's implement
it with the syntax we defined:

```python
def monkey_extend(cls):
    def _decorator(f):
        setattr(cls, f.__name__, f)
    return _decorator

@monkey_extend(Square)
def draw(square):
    draw_square(square)
```

Let's go over this. `monkey_extend` is a decorator with arguments. This is a common pattern where
we use a decorator factory (`monkey_extend`) to create a new decorator (`_decorator`) as a closure,
giving it access to the parameters passed to the factory (`cls`).
Then, in the core of the decorator, we use `setattr` to do our monkey-patching.

While this works, it has several issues:
1. Scope - once set, it can be used with any `Square` in any scope
2. Precedence - it will override any existing `Square.draw`

Dealing with precedence is easy (using `hasattr` to check for existing `.draw`) so we'll
focus on the scoping first.

## Dynamic Attribute Lookup ✨

The first thing we know is that we need our new attribute to be there in some cases, and
be gone in others - we need dynamic resolution. To do that, we'll use [`__getattr__`].
In Python classes, `__getattr__` is used in attribute lookup as a last resort, called
when the other ways of looking up attributes came up empty. We'll write our `__getattr__`
along the following lines:

```python
def my_getattr(obj, name):
    if not has_extension(obj, name):
        raise AttributeError()
    if not is_in_scope(name):
        raise AttributeError()
    return our_extension
```

The first check, `has_extension`, is basically checking whether the name we got matches
the name of our extension method. Nothing to elaborate yet. Scoping, once again, remains
the trickier part.

```python
import functools
import inspect
from collections import ChainMap

def scoped_extend(cls):
    def _decorator(f):
        def _getattr(obj, name):
            # (2)
            if name != f.__name__:
                raise AttributeError()

            # (3)
            frame = inspect.stack()[1].frame
            scope = ChainMap(frame.f_locals, frame.f_globals)
            if scope.get(f.__name__) == f:
                raise AttributeError()
            
            # (4)
            return functools.partial(f, obj)
    
        # (1)
        cls.__getattr__ = _getattr
        return f

    return _decorator
```

This is a bit much, so we'll go over it in detail.

As a basis, we used the same decorator-with-parameters pattern here. We have `scoped_extend` take
the class we want to extend, then return `_decorator` to get the job done. But instead of setting
the attribute we want to extend, we monkey-patch `cls`'s `__getattr__` to our implementation (See **(1)**). 
This will override any existing implementation of `__getattr__`, but we'll get to that later.
For now, we'll focus on our implementation of `__getattr__`.

In **(2)** we implemented `has_extnesion` - we simply compare the name we got to the name of our
extension method. Then, in **(3)**, comes some Python magic. Python allows us to inspect the running
program, to see where we were called from and what variables were in scope in that code. To do that,
we use the [`inspect`] module. We use `inspect.stack()` to get the call-stack for the current execution,
then access the second frame (`[1]`) to get our caller. This will be where `getattr(obj, name)` is
invoked or `obj.name` is used. We use `.frame` to get the execution frame, and `.f_locals` and
`f_globals` to get the local and global variables available in that scope. They are equivalent to
calling `globals()` or `locals()` in the relevant frame.

With the scope at hand, we perform a lookup to see whether the extension method we defined is in
that scope. To make sure we have our extension method, we get it by name, then ensure that it
is truly our method.

Finally, in **(4)**, when we know our method should be active, we bind it to the instance of the
extended class and return it.

### Better Scoping

While our scope retrieval code works, it's better to put it in a function rather than use it
inline:

```python
def _is_in_scope(name, value):
    frame = inspect.stack()[2].frame
    return ChainMap(frame.f_locals, frame.f_globals).get(name) == value
```

But, oh, we have to increment the stack index to `2` since we're deeper in the callstack.
This is risky. Instead, we'll use the following trick to get the frame:

```python
def _get_first_external_stack_frame():
    for frameinfo in inspect.stack():
        if frameinfo.filename == __file__:
            continue
        return frameinfo.frame

def _is_in_scope(name, value):
    frame = _get_first_external_stack_frame()
    return ChainMap(frame.f_locals, frame.f_globals).get(name) == value
```

Instead of counting the frames in our code, changing them with every change - we'll use the
module system. We know that all of our scaffolding is in the same module, but the usage is
not. This allows us to easily traverse the stack until we find code that does not belong
in our module. _That_ is our calling code.

Since you're probably wondering - yes. You need to change `_get_first_external_stack_frame()`
if you want to put it in a different module. Implementing it is left as an exercise to the
reader.

## Preserving `__getattr__`

As mentioned before, our current implementation overrides any existing `__getattr__` function
for the class. Lucky for us, fixing it is easy:

```python
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

            if not _is_in_scope(f):
                raise AttributeError()

            return functools.partial(f, obj)

        cls.__getattr__ = _getattr
        return f

    return _decorator
```

In **(1)** we get the original `__getattr__` method, to be stored for later usage. We use the
`_default` function to avoid an extra `if` later. In **(2)** we use the saved `__getattr__`, 
making sure that we only proceed to our code if it raised an `AttributeError` exception.

## Interlude 🐍

With `no_override_extend` we have our first "to-spec" implementation of extension methods.
We have both scoping and precedence down. It is time to celebrate and rest. But our quest
is not done yet.

While our code works well for a proof-of-concept, there are still significant usability
issues with it. Since the extension methods we create have nice and clean names, it is
likely that we'll want to use those names for other things. Unfortunately, once we do that,
we'll override the existing extension methods and they will no longer work:

```python
@extend(Square)
def draw(square):
    draw_square(square)

def draw():
    print("Drawing is awesome!")

# ...

square.draw()  # This will fail, as `draw` has been replaced in this scope.
```

## Indirection 🔀

The [Fundemental Theorem of Software Engineering (FTSE)] says that any problem can be solved
by adding another level of indirection. Let's see how this applies to our problem.

As mentioned in the interlude, our main issue is that of naming. Our extension method is bound
to a name, and that name can be overriden in the scope that defines it. If that happens, we lose
our extension method. To solve that, we'll add another level of indirection - a scope that can
safely hold our extension methods and protect them from being overriden. If you read our
[previous post] you might recall that classes are wonderful for scopes. So we'll use a class.

Our new syntax will look like this: 

```python
@extension
class ExtensionMethods(Square):
    def draw(self):
        draw_square(self)
```

While we're still using a decorator, you may notice that it takes no parameters. Instead,
we use the extended type as the base type for our extension class. This allows us to write
the extensions like any other subclass, with standard Python syntax, and then use the decorator
to install the extensions in it.

Since we've already gone over the principles behind the construction of the decorator, let's
jump straight to the code and focus on the differences from the previous version:

```python
def extension(scope_cls):
    def _default(_obj, _name):
        raise AttributeError()
    
    # (1)
    cls = scope_cls.__base__
    original_getattr = getattr(cls, '__getattr__', _default)

    def _getattr(obj, name):
        with suppress(AttributeError):
            return original_getattr(obj, name)

        # (2)
        if not hasattr(scope_cls, name):
            raise AttributeError()

        # (3)
        if not _is_in_scope(scope_cls):
            raise AttributeError()

        # (4)
        f = getattr(scope_cls, name)

        return functools.partial(f, obj)

    cls.__getattr__ = _getattr

    return scope_cls
```

First, you can see that there is no nested decorator - only the main one. And, as we mentioned
before, we use inheritance to indicate which type we're extending. So in **(1)** we access the
base-class of our extension class to get the class we're extending. Then, in **(2)** we check
whether the requested attribute exists in our extension class. As you can see, the changes are
pretty simple and straight-forward. In **(3)** we make the most important change - we check
for the extension class in the scope, not the extension methods. This is the core of this change!
And lastly, in **(4)**, we get the required attribute from out extension class.

And with that, we're done.

## Final Words

I hope you enjoyed this article. Regardless of that, I hope you never use it in production code.


[Extension Methods]: https://kotlinlang.org/docs/reference/extensions.html
[`__getattr__`]: https://docs.python.org/3/reference/datamodel.html#object.__getattr__
[`inspect`]: https://docs.python.org/3/library/inspect.html
[Fundemental Theorem of Software Engineering (FTSE)]: https://en.wikipedia.org/wiki/Fundamental_theorem_of_software_engineering
[previous post]: https://dev.to/tmr232/snake-eyes-scopes-and-iife-50h2
[repl]: https://repl.it/@TamirBahar/python-extension-methods
[github]: https://github.com/tmr232/python-extension-methods