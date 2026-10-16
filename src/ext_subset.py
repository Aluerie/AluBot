"""Extensions to load (ETL)."""

EXT_SUBSET: dict[str, list[str]] = {
    "community": [
        # "moderation",
    ],
    "dev": [
        # "sync",
    ],
    "mimics": [
        # "embed_fixer",
    ],
    'uncategorized': [
        'tools'
    ]
}

LOAD_ALL_EXTENSIONS: bool = False
