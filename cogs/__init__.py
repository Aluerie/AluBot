from pkgutil import iter_modules

try:
    from _test import TEST_EXTENSIONS
except ModuleNotFoundError:
    TEST_EXTENSIONS = tuple()

# EXTENSIONS
IGNORED_EXTENSIONS = (
    'cogs.beta',
)
INITIAL_EXTENSIONS = ("jishaku",)
MY_EXTENSIONS = tuple(module.name for module in iter_modules(__path__, f'{__package__}.'))

ALL_EXTENSIONS = INITIAL_EXTENSIONS + MY_EXTENSIONS

EXTENSIONS = tuple(x for x in ALL_EXTENSIONS if x not in IGNORED_EXTENSIONS)

# TEST EXTENSIONS
TEST_EXTENSIONS = tuple(f'cogs.{x}' if x not in INITIAL_EXTENSIONS else x for x in TEST_EXTENSIONS)


def get_extensions(test: bool):
    if test:
        return TEST_EXTENSIONS
    else:
        return EXTENSIONS
