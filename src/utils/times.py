# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Slash command options for times that users type in; the parsing itself is `shared.timeparse`."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from discord import app_commands

from shared import clock, errors
from shared.scheduler import UTC
from shared.timeparse import ParsedTime, describe, parse_time

if TYPE_CHECKING:
    from core import Interaction

__all__ = ("TimeTransformer",)


class TimeTransformer(app_commands.Transformer):
    """Slash command option for a time in the future, understood in the user's timezone.

    The autocomplete shows how the input is understood before it's sent.
    """

    @override
    async def transform(self, interaction: Interaction, value: str) -> ParsedTime:  # ty: ignore[invalid-method-override]
        timezone = await interaction.client.tz_manager.get_timezone(interaction.user.id) or UTC
        return parse_time(value, now=interaction.created_at, timezone=timezone)

    @override
    async def autocomplete(self, interaction: Interaction, value: str) -> list[app_commands.Choice[str]]:  # ty: ignore[invalid-method-override]
        if not value.strip():
            examples = ("1h", "tomorrow 9am", "friday 18:00", "eow", "in 3 days")
            return [app_commands.Choice(name=example, value=example) for example in examples]

        timezone = await interaction.client.tz_manager.get_timezone(interaction.user.id) or UTC
        now = clock.utcnow()
        try:
            parsed = parse_time(value, now=now, timezone=timezone)
        except errors.BadUserInputError as exc:
            name = f"❌ {exc}"
        else:
            name = f"{value} → {describe(parsed, now=now, timezone=timezone)}"
        return [app_commands.Choice(name=name[:100], value=value[:100])]
