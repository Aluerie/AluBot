from pkgutil import iter_modules

try:
    from _test import TEST_EXTENSIONS, IGNORE_TEST
except ModuleNotFoundError:
    TEST_EXTENSIONS = tuple()

# EXTENSIONS
IGNORED_EXTENSIONS = ('cogs.beta',)
INITIAL_EXTENSIONS = ("jishaku",)


def get_extensions(test: bool):
    if test and not IGNORE_TEST:
        return tuple(f'cogs.{x}' if x not in INITIAL_EXTENSIONS else x for x in TEST_EXTENSIONS)
    else:
        my_extensions = tuple(module.name for module in iter_modules(__path__, f'{__package__}.'))
        all_extensions = INITIAL_EXTENSIONS + my_extensions
        return tuple(x for x in all_extensions if x not in IGNORED_EXTENSIONS)
