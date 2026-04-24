"""
edit.py - Modernized buffer editing for Sublime Text 3+ (Pawn Syntax Package)
Provides a clean API for performing multiple edit operations as a single undo step.
Backward compatibility with Sublime Text 2 is removed; use ST3+ modern APIs.
"""

import inspect
import sublime
import sublime_plugin


def run_callback(callback, view, edit, *args, **kwargs):
    """
    Safely invoke a callback function that may optionally accept (view, edit).
    
    If the callback's signature does not accept arguments, just call it.
    Otherwise, pass (view, edit, *args, **kwargs).
    """
    try:
        spec = inspect.signature(callback)
        params = list(spec.parameters.keys())
    except (ValueError, TypeError):
        # If signature() fails, fall back to safe call with try/except
        try:
            callback(view, edit, *args, **kwargs)
        except TypeError:
            callback()
        return

    if not params:
        callback()
    else:
        callback(view, edit, *args, **kwargs)


class EditFuture:
    """Lazily resolved value that captures a function and calls it later with (view, edit)."""
    def __init__(self, func):
        self.func = func

    def resolve(self, view, edit):
        return self.func(view, edit)


class EditStep:
    """Represents a single edit operation (insert, erase, replace) or a callback."""
    def __init__(self, cmd, *args):
        if cmd not in ('insert', 'erase', 'replace', 'callback'):
            raise ValueError(f"Unknown edit command: {cmd}")
        self.cmd = cmd
        self.args = args

    def run(self, view, edit):
        if self.cmd == 'callback':
            run_callback(self.args[0], view, edit)
            return

        func_map = {
            'insert': view.insert,
            'erase': view.erase,
            'replace': view.replace,
        }
        func = func_map[self.cmd]
        resolved_args = self._resolve_args(view, edit)
        func(edit, *resolved_args)

    def _resolve_args(self, view, edit):
        """Resolve any EditFuture objects in the arguments before passing them."""
        resolved = []
        for arg in self.args:
            if isinstance(arg, EditFuture):
                resolved.append(arg.resolve(view, edit))
            else:
                resolved.append(arg)
        return resolved


class Edit:
    """
    Collects multiple text operations and applies them as a single atomic edit.
    
    Usage:
        with Edit(view) as edit:
            edit.insert(0, '// New comment\n')
            edit.replace(some_region, 'replacement text')
            edit.callback(lambda v, e: print(f"Done editing {v.id()}"))
    """
    def __init__(self, view):
        self.view = view
        self.steps = []

    def __bool__(self):
        """Python 3 truthiness check."""
        return bool(self.steps)

    __nonzero__ = __bool__  # Python 2 compatibility

    @classmethod
    def future(cls, func):
        """Create a lazy value that evaluates to func(view, edit) when the edit runs."""
        return EditFuture(func)

    def step(self, cmd, *args):
        """Add a raw edit step. Prefer using insert/erase/replace/callback methods."""
        self.steps.append(EditStep(cmd, *args))

    def insert(self, point, string):
        """Insert string at the given point in the buffer."""
        self.steps.append(EditStep('insert', point, string))

    def erase(self, region):
        """Erase the text within a sublime.Region."""
        self.steps.append(EditStep('erase', region))

    def replace(self, region, string):
        """Replace text within a region with a new string."""
        self.steps.append(EditStep('replace', region, string))

    def callback(self, func, *args, **kwargs):
        """
        Schedule a function to run during the edit.
        The function can optionally receive (view, edit, *args, **kwargs).
        """
        self.steps.append(EditStep('callback', func, *args, **kwargs))

    def run(self, view, edit):
        """Execute all accumulated edit steps."""
        for step in self.steps:
            step.run(view, edit)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            # Exception occurred; do not apply the edit
            return False

        # Sublime Text 3+ only
        key = str(id(self))
        sublime.edit_storage[key] = self.run
        self.view.run_command('apply_edit', {'key': key})


class ApplyEditCommand(sublime_plugin.TextCommand):
    """
    Internal command that executes a stored edit function.
    Matches the format expected by the Edit class above.
    """
    def run(self, edit, key):
        stored_func = sublime.edit_storage.pop(key, None)
        if stored_func is not None:
            stored_func(self.view, edit)
        else:
            print(f"[Pawn Syntax] Warning: No edit storage found for key: {key}")


# ---- Module-Level Utilities ----

def edit_with_callbacks(view, callbacks):
    """
    High-level helper: apply a list of callback functions as a single atomic edit.
    
    Args:
        view: sublime.View instance.
        callbacks: Iterable of functions, each optionally accepting (view, edit).
    """
    with Edit(view) as editor:
        for callback in callbacks:
            editor.callback(callback)