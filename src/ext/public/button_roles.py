"""Button Roles.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import re
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, Self, override

import discord
from discord import app_commands, ui

from core import Cog, Modal, View

if TYPE_CHECKING:
    from core import Bot, Interaction

# `button-role:123` toggles a role, `button-role:123:x` does the same but is part of an "exclusive" message.
# Messages sent before exclusive mode existed use the first form, so they keep working.
ROLE_BUTTON_RE = re.compile(r"button-role:(?P<role_id>[0-9]+)(?P<exclusive>:x)?")
HEX_COLOR_RE = re.compile(r"[0-9a-fA-F]{6}")


def role_ids_from_message(message: discord.Message) -> set[int]:
    """Collect role IDs from the role buttons of a message.

    Parameters
    ----------
    message
        Message to scan.
    """
    role_ids: set[int] = set()
    for row in message.components:
        if not isinstance(row, discord.ActionRow):
            continue
        for component in row.children:
            if (
                isinstance(component, discord.Button)
                and component.custom_id
                and (match := ROLE_BUTTON_RE.fullmatch(component.custom_id))
            ):
                role_ids.add(int(match["role_id"]))
    return role_ids


def text_value(label: ui.Label[Any]) -> str:
    """Get the text typed into a `Label` that wraps a `TextInput`.

    Parameters
    ----------
    label
        Label to read the value from.
    """
    component = label.component
    assert isinstance(component, ui.TextInput)
    return component.value


def selected_roles(label: ui.Label[Any]) -> list[discord.Role]:
    """Get the roles picked in a `Label` that wraps a `RoleSelect`.

    Parameters
    ----------
    label
        Label to read the roles from.
    """
    component = label.component
    assert isinstance(component, ui.RoleSelect)
    return list(component.values)


def uploaded_files(label: ui.Label[Any]) -> list[discord.Attachment]:
    """Get the files uploaded in a `Label` that wraps a `FileUpload`.

    Parameters
    ----------
    label
        Label to read the files from.
    """
    component = label.component
    assert isinstance(component, ui.FileUpload)
    return list(component.values)


def is_checked(label: ui.Label[Any]) -> bool:
    """Get whether the checkbox in a `Label` that wraps a `Checkbox` was ticked.

    Parameters
    ----------
    label
        Label to read the value from.
    """
    component = label.component
    assert isinstance(component, ui.Checkbox)
    return bool(component.value)


class RoleButton(ui.DynamicItem[ui.Button[Any]], template=ROLE_BUTTON_RE):
    """Persistent button that toggles a role for the member who clicks it.

    Everything it needs is stored in the `custom_id`, so no database is needed. In an exclusive message,
    picking a role also removes the member's other roles from the buttons of that same message.

    Parameters
    ----------
    role_id
        ID of the role to toggle.
    label
        Text on the button.
    exclusive
        Whether the member can hold only one role from the message at a time.
    """

    def __init__(self, role_id: int, label: str | None = None, *, exclusive: bool = False) -> None:
        super().__init__(
            ui.Button(
                label=label,
                style=discord.ButtonStyle.secondary,
                custom_id=f"button-role:{role_id}{':x' if exclusive else ''}",
            ),
        )
        self.role_id: int = role_id
        self.exclusive: bool = exclusive

    @classmethod
    @override
    async def from_custom_id(cls, interaction: Interaction, item: ui.Item[Any], match: re.Match[str], /) -> Self:
        return cls(int(match["role_id"]), exclusive=match["exclusive"] is not None)

    @override
    async def callback(self, interaction: Interaction) -> None:
        assert interaction.guild
        assert interaction.message
        assert isinstance(interaction.user, discord.Member)

        # Role requests can be slow when rate limited, so acknowledge the interaction right away.
        await interaction.response.defer(ephemeral=True, thinking=True)

        member = interaction.user
        role = interaction.guild.get_role(self.role_id)
        if role is None:
            await interaction.followup.send("This role does not exist anymore.")
            return

        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Button Roles")
                content = f"Removed {role.mention}"
            else:
                to_remove: list[discord.Role] = []
                if self.exclusive:
                    sibling_ids = role_ids_from_message(interaction.message) - {role.id}
                    to_remove = [r for r in member.roles if r.id in sibling_ids]

                if to_remove:
                    await member.remove_roles(*to_remove, reason="Button Roles (exclusive)")
                    await member.add_roles(role, reason="Button Roles (exclusive)")
                    removed = ", ".join(r.mention for r in to_remove)
                    content = f"Added {role.mention}, removed {removed}"
                else:
                    await member.add_roles(role, reason="Button Roles")
                    content = f"Added {role.mention}"
        except discord.Forbidden:
            content = f"I can't manage {role.mention}. Please tell the moderators to move my top role above it."
        except discord.HTTPException:
            content = "Something went wrong while changing your roles. Please try again later."

        await interaction.followup.send(content, allowed_mentions=discord.AllowedMentions.none())


class ButtonRolesView(View):
    """View with a button per role, laid out five per row.

    Parameters
    ----------
    roles
        Roles to create buttons for.
    exclusive
        Whether the member can hold only one role from the message at a time.
    """

    def __init__(self, roles: list[discord.Role], *, exclusive: bool = False) -> None:
        super().__init__(timeout=None)
        for role in roles:
            self.add_item(RoleButton(role.id, label=role.name[:80], exclusive=exclusive))


class ButtonRolesModal(Modal, title="Create Button Roles"):
    """Modal to collect the embed's look, the roles to make buttons for and whether they are exclusive."""

    description = ui.Label(
        text="Embed description",
        description="Markdown works. Start with `# ` for a title. Mention roles as <@&role-id>.",
        component=ui.TextInput(style=discord.TextStyle.paragraph, max_length=4000),
    )
    color = ui.Label(
        text="Embed color",
        description="Hex value, e.g. 3E2F84 (no # needed)",
        component=ui.TextInput(min_length=6, max_length=6, placeholder="3E2F84"),
    )
    image = ui.Label(
        text="Embed image",
        description="Optional. Upload an image to show at the bottom of the embed.",
        component=ui.FileUpload(min_values=0, max_values=1, required=False),
    )
    roles = ui.Label(
        text="Roles",
        description="Each role becomes a button (up to 25).",
        component=ui.RoleSelect(min_values=1, max_values=25),
    )
    exclusive = ui.Label(
        text="Exclusive",
        description="Members can hold only one of these roles at a time.",
        component=ui.Checkbox(default=False),
    )

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        assert interaction.guild
        assert isinstance(interaction.user, discord.Member)

        raw_color = text_value(self.color)
        if not HEX_COLOR_RE.fullmatch(raw_color):
            await interaction.response.send_message("Invalid hex color.", ephemeral=True)
            return
        color = discord.Colour(int(raw_color, 16))

        attachment = next(iter(uploaded_files(self.image)), None)
        if attachment is not None and not (attachment.content_type or "").startswith("image/"):
            await interaction.response.send_message("The uploaded file must be an image.", ephemeral=True)
            return

        roles = sorted(selected_roles(self.roles), key=lambda r: r.position, reverse=True)
        if unassignable := [r for r in roles if not r.is_assignable()]:
            mentions = ", ".join(r.mention for r in unassignable)
            await interaction.response.send_message(
                f"I can't assign: {mentions}. They are managed, `@everyone`, or above my top role.",
                ephemeral=True,
            )
            return

        # Otherwise a member could make a button for a role above their own and give it to themselves.
        if interaction.user.id != interaction.guild.owner_id and (
            too_high := [r for r in roles if r >= interaction.user.top_role]
        ):
            mentions = ", ".join(r.mention for r in too_high)
            await interaction.response.send_message(
                f"You can't create buttons for roles at or above your own top role: {mentions}.",
                ephemeral=True,
            )
            return

        # Downloading and re-uploading the image can take longer than the 3 seconds Discord gives us to respond.
        await interaction.response.defer(thinking=True)

        embed = discord.Embed(description=text_value(self.description), colour=color)
        files: list[discord.File] = []
        if attachment is not None:
            # The modal's attachment link is temporary, so re-upload it as a part of the message.
            # A plain filename also keeps the `attachment://` reference simple.
            file = await attachment.to_file(filename=f"banner{PurePath(attachment.filename).suffix}")
            files.append(file)
            embed.set_image(url=f"attachment://{file.filename}")

        await interaction.followup.send(
            embed=embed,
            files=files,
            view=ButtonRolesView(roles, exclusive=is_checked(self.exclusive)),
            allowed_mentions=discord.AllowedMentions.none(),
        )


class ButtonRoles(Cog):
    """Button Roles."""

    @override
    async def cog_load(self) -> None:
        await super().cog_load()
        self.bot.add_dynamic_items(RoleButton)

    @override
    async def cog_unload(self) -> None:
        await super().cog_unload()
        self.bot.remove_dynamic_items(RoleButton)

    button_roles_group = app_commands.Group(
        name="button-roles",
        description="Create and manage button roles.",
        allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=False, private_channel=False),
        allowed_installs=app_commands.AppInstallationType(guild=True, user=False),
        default_permissions=discord.Permissions(manage_roles=True),
    )

    @button_roles_group.command()
    async def create(self, interaction: Interaction) -> None:
        """🎨 Create a button roles message."""
        await interaction.response.send_modal(ButtonRolesModal())


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(ButtonRoles(bot))
