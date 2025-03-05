from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

import discord

from bot import AluContext, AluView
from utils import const

if TYPE_CHECKING:
    from collections.abc import Callable

    from bot import AluBot, AluInteraction


__all__ = ("Disambiguator",)


class ConfirmationView(AluView):
    def __init__(self, *, author_id: int, timeout: float) -> None:
        super().__init__(author_id=author_id, view_name="Confirmation Prompt", timeout=timeout)
        self.value: bool | None = None

    async def button_callback(self, interaction: AluInteraction, yes_no: bool) -> None:
        self.value = yes_no
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True  # type: ignore
        await interaction.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(emoji=const.Tick.Yes, label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: AluInteraction, _: discord.ui.Button[Self]) -> None:
        await self.button_callback(interaction, True)

    @discord.ui.button(emoji=const.Tick.No, label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: AluInteraction, _: discord.ui.Button[Self]) -> None:
        await self.button_callback(interaction, False)


class DisambiguatorView[T](AluView):
    selected: T

    def __init__(self, ctx_ntr: AluContext | AluInteraction, data: list[T], entry: Callable[[T], Any]) -> None:
        super().__init__(author_id=ctx_ntr.user.id, view_name="Select Menu")
        self.ctx_ntr: AluContext | AluInteraction = ctx_ntr
        self.data: list[T] = data

        options = []
        for i, x in enumerate(data):
            opt = entry(x)
            if not isinstance(opt, discord.SelectOption):
                opt = discord.SelectOption(label=str(opt))
            opt.value = str(i)
            options.append(opt)

        select = discord.ui.Select(options=options)

        select.callback = self.on_select_submit
        self.select = select
        self.add_item(select)

    async def on_select_submit(self, interaction: AluInteraction) -> None:
        index = int(self.select.values[0])
        self.selected = self.data[index]
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True  # type: ignore
        await interaction.edit_original_response(view=self)
        self.stop()


class Disambiguator:
    """Class having utilities to disambiguate user's input. Like.

    * confirmation prompt
        Just a simple Confirm/Cancel question.
    * disambiguate choices
        when user input is not clear, i.e. "oredange",
        so we ask them if they meant red or orange.
    """  # cSpell:ignore oredange

    async def send_message(
        self,
        ctx_ntr: AluContext | AluInteraction,
        embed: discord.Embed,
        view: discord.ui.View = discord.utils.MISSING,
        ephemeral: bool = True,
    ) -> discord.Message | discord.InteractionMessage:
        """Boiler plate function that replies for both cases of AluContext and AluInteraction."""
        if isinstance(ctx_ntr, AluContext):
            # Context
            return await ctx_ntr.reply(embed=embed, view=view, ephemeral=ephemeral)
        # Interaction
        if not ctx_ntr.response.is_done():
            await ctx_ntr.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
            return await ctx_ntr.original_response()
        return await ctx_ntr.followup.send(embed=embed, view=view, ephemeral=ephemeral, wait=True)

    async def confirm(
        self,
        ctx_ntr: AluContext | AluInteraction,
        embed: discord.Embed,
        *,
        timeout: float = 120.0,
        author_id: int | None = None,
        ephemeral: bool = False,
    ) -> bool | None:
        """Confirmation Prompt: An interactive buttons-based Confirm/Cancel dialog.

        Example of usage:
        >>> if not self.bot.disambiguator.confirm(ctx, confirm_embed):
        >>>     return

        Parameters
        ----------
        ctx_ntr : AluContext | AluInteraction
            context object to send confirmation with.
        embed : discord.Embed
            Embed to show along with the prompt.
        timeout : float, optional
            How long to wait before returning., by default 120.0
        author_id: Optional[int]
            The member who should respond to the prompt. Defaults to the author of the
            Context's message.

        Returns
        -------
        Optional[bool]
            ``True`` if explicit confirm,
            ``False`` if explicit deny,
            ``None`` if deny due to timeout

        """
        author_id = author_id or ctx_ntr.user.id
        view = ConfirmationView(author_id=author_id, timeout=timeout)
        view.message = await self.send_message(ctx_ntr, embed, view, ephemeral=ephemeral)
        await view.wait()

        if view.value is None:
            desc = "The Confirmation Prompt time-outed without receiving a response."
        elif not view.value:
            desc = f"You pressed {const.Tick.Yes}`Cancel`."
        else:
            # view.value is True so we just return it
            return view.value

        # we want to send universally applicable embed
        cancel_embed = discord.Embed(
            color=discord.Color.yellow(),
            description=f"{desc} Thus, canceling the operation.",
        )
        await self.send_message(ctx_ntr, cancel_embed)
        return view.value

    async def disambiguate[T](
        self,
        ctx_ntr: AluContext | AluInteraction,
        matches: list[T],
        entry: Callable[[T], Any],
        *,
        ephemeral: bool = False,
    ) -> T:
        """_summary_.

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        ValueError
            _description_
        ValueError
            _description_

        """
        amount_of_matches = len(matches)

        if amount_of_matches == 0:
            msg = "No results found."
            raise ValueError(msg)
        if amount_of_matches == 1:
            return matches[0]
        if amount_of_matches > 25:
            msg = "Too many results... sorry."
            raise ValueError(msg)

        view = DisambiguatorView(ctx_ntr, matches, entry)
        embed = discord.Embed(color=discord.Color.dark_gray())
        embed.description = "There are too many matches... Which one did you mean?"

        view.message = await self.send_message(ctx_ntr, embed, view, ephemeral=ephemeral)

        await view.wait()
        return view.selected
