# Python Module Reloader
#
# Copyright (c) 2009, 2010, 2011 Jon Parise <jon@indelible.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Python Module Reloader"""

try:
    import builtins
except ImportError:
    #python 2.x
    import __builtin__ as builtins

import imp
import sys

__author__ = 'Jon Parise <jon@indelible.org>'
__version__ = '0.3'

__all__ = ('enable', 'disable', 'get_dependencies', 'reload')

_baseimport = builtins.__import__
_parents = dict()
_parent = None

def enable():
    """Enable global module dependency tracking."""
    builtins.__import__ = _import

def disable():
    """Disable global module dependency tracking."""
    builtins.__import__ = _baseimport
    _parents.clear()
    _parent = None

def get_parents(m):
    """Get the dependency list for the given imported module."""
    return _parents.get(m.__name__, None)

def _deepcopy_module_dict(m):
    """Make a deep copy of a module's dictionary."""
    import copy

    # We can't deepcopy() everything in the module's dictionary because some
    # items, such as '__builtins__', aren't deepcopy()-able.  To work around
    # that, we start by making a shallow copy of the dictionary, giving us a
    # way to remove keys before performing the deep copy.
    d = vars(m).copy()
    del d['__builtins__']
    return copy.deepcopy(d)

def _reload(m, visited):
    """Internal module reloading routine."""
    name = getattr(m, '__name__', None)

    # Start by adding this module to our set of visited modules.  We use this
    # set to avoid running into infinite recursion while walking the module
    # dependency graph.
    visited.add(m)

    if name is None:
        return


    # Because we're triggering a reload and not an import, the module itself
    # won't run through our _import hook below.  In order for this module's
    # dependencies (which will pass through the _import hook) to be associated
    # with this module, we need to set our parent pointer beforehand.
    global _parent
    _parent = name

    # If the module has a __reload__(d) function, we'll call it with a copy of
    # the original module's dictionary after it's been reloaded.
    callback = getattr(m, '__reload__', None)
    if callback is not None:
        d = _deepcopy_module_dict(m)
        imp.reload(m)
        callback(d)
    else:
        imp.reload(m)

    # Reset our parent pointer now that the reloading operation is complete.
    _parent = None

    # follow our parents so they can grab the changes we made to ourself
    parents = _parents.get(name)
    if parents is not None:
        for parent in parents:
            if parent not in visited:
                _reload(parent, visited)



def reload(m):
    """Reload an existing module.

    Any known dependencies of the module will also be reloaded.

    If a module has a __reload__(d) function, it will be called with a copy of
    the original module's dictionary after the module is reloaded."""
    _reload(m, set())

def _import(name, globals=None, locals=None, fromlist=None, level=-1):
    """__import__() replacement function that tracks module dependencies."""
    # Track our current parent module.  This is used to find our current place
    # in the dependency graph.
    global _parent
    parent = _parent
    _parent = name

    if globals is None:
        globals = sys._getframe(1).f_globals
    if locals is None:
        locals = {}
    if fromlist is None:
        fromlist = []

    # Perform the actual import using the base import function.  We get the
    # module directly from sys.modules because the import function only
    # returns the top-level module reference for a nested import statement
    # (e.g. `import package.module`).
    m = _baseimport(name, globals, locals, fromlist, level)
    sysentry = sys.modules.get(name, None)

    # If we have a parent (i.e. this is a nested import) and this is a
    # reloadable (source-based) module, we append ourself to our parent's
    # dependency list.
    if parent is not None and hasattr(sysentry, '__file__'):
        parent_entry = sys.modules.get(parent)
        if parent_entry:
            l = _parents.setdefault(name,set())
            l.add(parent_entry)

    # Lastly, we always restore our global _parent pointer.
    _parent = parent

    return m
