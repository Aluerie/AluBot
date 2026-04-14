"""Extensions to load (ETL)."""

categories: dict[str, list[str]] = {
    "community": [
        # "moderation",
    ],
    "dev": [
        # "sync",
    ],
}

EXTENSIONS_TO_LOAD: tuple[str, ...] = (
    # Categorized extensions
    *tuple(
        f"ext.{category}.{extension}"
        for category, extensions in categories.items()
        for extension in extensions
        if extensions
    ),
    # Extras
    "ext.beta",
    # Extra extra
    # "ext.meta.meta.help",
)


LOAD_ALL_EXTENSIONS: bool = False
