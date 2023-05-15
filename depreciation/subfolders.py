import os
from pkgutil import iter_modules

try:
    from _test import TEST_EXTENSIONS
except ModuleNotFoundError:
    TEST_EXTENSIONS = tuple()


# EXTENSIONS
IGNORED_EXTENSIONS = ('beta',)
INITIAL_EXTENSIONS = ("jishaku",)

# Packages
MY_PACKAGES = tuple(module.name for module in iter_modules(path=__path__))  # , prefix=f'{__package__}.'


def get_extensions(test: bool) -> tuple:
    if test and TEST_EXTENSIONS:
        test_packages = tuple(x for x in TEST_EXTENSIONS if x in MY_PACKAGES)

        non_ext_subfolders = [x for x in TEST_EXTENSIONS if x not in MY_PACKAGES]
        my_extensions = tuple(f'cogs.{x}' if x not in INITIAL_EXTENSIONS else x for x in test_packages)
    else:
        subfolders = [f.name for f in os.scandir('cogs') if f.is_dir() if not f.name.startswith('_')]

        non_ext_subfolders = [x for x in subfolders if x not in MY_PACKAGES]
        my_extensions = INITIAL_EXTENSIONS + tuple(f'cogs.{x}' for x in MY_PACKAGES if x not in IGNORED_EXTENSIONS)

    subfolder_extensions = tuple(
        module.name
        for sf in non_ext_subfolders
        for module in iter_modules(path=[f'cogs\\{sf}'], prefix=f'cogs.{sf}.')
    )

    extensions = my_extensions + subfolder_extensions
    print(extensions)
    return extensions
