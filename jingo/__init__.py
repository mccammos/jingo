"""Adapter for using Jinja2 with Django."""

from django import http
from django.conf import settings
from django.template.context import get_standard_processors

import jinja2

VERSION = (0, 3)
__version__ = '.'.join(map(str, VERSION))


_helpers_loaded = False


def get_env():
    """Configure and return a jinja2 Environment."""
    # Mimic Django's setup by loading templates from directories in
    # TEMPLATE_DIRS and packages in INSTALLED_APPS.
    x = ((jinja2.FileSystemLoader, settings.TEMPLATE_DIRS),
         (jinja2.PackageLoader, settings.INSTALLED_APPS))
    loaders = [loader(p) for loader, places in x for p in places]

    opts = {'trim_blocks': True,
            'extensions': ['jinja2.ext.i18n'],
            'autoescape': True,
            'auto_reload': settings.DEBUG,
            'loader': jinja2.ChoiceLoader(loaders),
            }

    if hasattr(settings, 'JINJA_CONFIG'):
        if hasattr(settings.JINJA_CONFIG, '__call__'):
            config = settings.JINJA_CONFIG()
        else:
            config = settings.JINJA_CONFIG
        opts.update(config)

    e = jinja2.Environment(**opts)
    # TODO: use real translations
    e.install_null_translations()
    return e


def render(request, template, context=None, **kwargs):
    """
    Shortcut like Django's ``render_to_response``, but better.

    Minimal usage, with only a request object and a template name::

        return jingo.render(request, 'template.html')

    With template context and keywords passed to
    :class:`django.http.HttpResponse`::

        return jingo.render(request, 'template.html',
                            {'some_var': 42}, status=209)
    """
    if not _helpers_loaded:
        load_helpers()

    if context is None:
        context = {}
    for processor in get_standard_processors():
        context.update(processor(request))
    # If it's not a Template, it must be a path to be loaded.
    if not isinstance(template, jinja2.environment.Template):
        template = env.get_template(template)
    rendered = template.render(**context)
    return http.HttpResponse(rendered, **kwargs)


def load_helpers():
    """Try to import ``helpers.py`` from each app in INSTALLED_APPS."""
    # We want to wait as long as possible to load helpers so there aren't any
    # weird circular imports with jingo.
    global _helpers_loaded
    from . import helpers
    for app in settings.INSTALLED_APPS:
        try:
            __import__('%s.helpers' % app)
        except ImportError:
            pass
    _helpers_loaded = True


class Register(object):
    """Decorators to add filters and functions to the template Environment."""

    def __init__(self, env):
        self.env = env

    def filter(self, f):
        """Adds the decorated function to Jinja's filter library."""
        self.env.filters[f.__name__] = f
        return f

    def function(self, f):
        """Adds the decorated function to Jinja's global namespace."""
        self.env.globals[f.__name__] = f
        return f


env = get_env()
register = Register(env)
