"""List of extensions to test

* Rename this file to `_test.py`.
* List extensions to test under `TEST_EXTENSIONS` tuple
    * the names should be listed without `extensions.` prefix, i.e. `'community.moderation'`
    * to ignore the list and use all extensions anyway - set the variable USE_ALL_EXTENSIONS to True
"""

TEST_EXTENSIONS = (
    "dev.sync",
    # 'dev.reload',
    # 'dev.utilities',
    # 'community.moderation'
    # 'hideout.scrape',
    # "dota_news.bugtracker",
    #####################################
    # 'meta.meta.help',
    # 'jebaited.lewd',
    # 'jebaited.embedmaker',
    # 'community.fix_links',
    # 'info.schedule',
    "community.twtv",
    # 'fpc_notifications.dota',
    # 'fpc_notifications.trusted'
    # 'meta.meta',
    # 'educational.language'
    # "beta",
    # "reminders.reminders",
    # "user_settings.timezone",
)

# Change this to `True` if you want to run all extensions on the test bot anyway
USE_ALL_EXTENSIONS = False
