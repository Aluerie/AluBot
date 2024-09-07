    # POST MATCH EDITS
    async def edit_with_opendota(
        self, match_id: int, friend_id: int, hero_id: int, channel_message_tuples: list[tuple[int, int]]
    ) -> bool:
        try:
            opendota_match = await self.bot.opendota_client.get_match(match_id=match_id)
        except aiohttp.ClientResponseError as exc:
            edit_log.debug("OpenDota API Response Not OK with status %s", exc.status)
            return False

        if "radiant_win" not in opendota_match:
            # Somebody abandoned before the first blood or so -> game didn't count
            # thus "radiant_win" key is not present
            edit_log.debug("Opendota: match %s did not count. Deleting the match.", match_id)
            not_counted_match_to_edit = NotCountedMatchToEdit(self.bot)
            await self.edit_match(not_counted_match_to_edit, channel_message_tuples, pop=True)
            await self.cleanup_match_to_edit(match_id, friend_id)
            return True

        for player in opendota_match["players"]:
            if player["hero_id"] == hero_id:
                opendota_player = player
                break
        else:
            raise RuntimeError(f"Somehow the player {friend_id} is not in the match {match_id}")

        match_to_edit_with_opendota = DotaFPCMatchToEditWithOpenDota(self.bot, player=opendota_player)
        await self.edit_match(match_to_edit_with_opendota, channel_message_tuples)
        return True










class DotaFPCMatchToEditWithOpenDota(BaseMatchToEdit):
    """
    Class
    """

    def __init__(
        self,
        bot: AluBot,
        *,
        player: dota.OpenDotaAPISchema.Player,
    ):
        super().__init__(bot)

        self.outcome: str = "Win" if player["win"] else "Loss"
        self.kda: str = f'{player["kills"]}/{player["deaths"]}/{player["assists"]}'

        self.ability_upgrades_ids: list[int] = player["ability_upgrades_arr"][:18]

        self.item_ids: list[int] = [player[f"item_{i}"] for i in range(6)]
        if player["aghanims_shard"]:
            self.item_ids.append(const.DOTA.AGHANIMS_SHARD_ITEM_ID)
        if player["aghanims_scepter"]:
            self.item_ids.append(const.DOTA.AGHANIMS_BLESSING_ITEM_ID)

        self.neutral_item_id: int = player["item_neutral"]

    def __repr__(self) -> str:
        pairs = " ".join([f"{k}={v!r}" for k, v in self.__dict__.items()])
        return f"<{self.__class__.__name__} {pairs}>"

    @override
    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour) -> Image.Image:
        img = await self.bot.transposer.url_to_image(embed_image_url)

        item_icon_urls = [await self.bot.dota_cache.item.icon_by_id(item_id) for item_id in self.item_ids]
        item_icon_images = [await self.bot.transposer.url_to_image(url) for url in item_icon_urls]

        neutral_item_url = await self.bot.dota_cache.item.icon_by_id(self.neutral_item_id)
        neutral_item_image = await self.bot.transposer.url_to_image(neutral_item_url)

        ability_icon_urls = [await self.bot.dota_cache.ability.icon_by_id(id) for id in self.ability_upgrades_ids]
        ability_icon_images = [await self.bot.transposer.url_to_image(url) for url in ability_icon_urls]

        talent_names = []
        for ability_upgrade in self.ability_upgrades_ids:
            talent_name = await self.bot.dota_cache.ability.talent_by_id(ability_upgrade)
            if talent_name is not None:
                talent_names.append(talent_name)

        def build_notification_image() -> Image.Image:
            log.debug("Building edited notification message.")
            width, height = img.size
            information_height = 50
            rectangle = Image.new("RGB", (width, information_height), str(colour))
            ImageDraw.Draw(rectangle)
            img.paste(rectangle, (0, height - information_height))
            draw = ImageDraw.Draw(img)

            for count, item_image in enumerate(item_icon_images):
                # item image
                item_image = item_image.resize((69, information_height))  # 69/50 - to match 88/64 which is natural size
                left = count * item_image.width
                img.paste(item_image, (left, height - item_image.height))

            resized_neutral_item_image = i = neutral_item_image.resize((69, information_height))
            img.paste(im=i, box=(width - i.width, height - i.height))

            # abilities
            ability_h = 37
            for count, ability_image in enumerate(ability_icon_images):
                ability_image = ability_image.resize((ability_h, ability_h))
                img.paste(ability_image, (count * ability_h, height - information_height - ability_image.height))

            # talents
            talent_font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 12)
            for count, talent_text in enumerate(talent_names):
                talent_text_w, talent_text_h = self.bot.transposer.get_text_wh(talent_text, talent_font)
                draw.text(
                    xy=(width - talent_text_w, height - information_height - 30 * 2 - 22 * count),
                    text=talent_text,
                    font=talent_font,
                    align="right",
                )

            # kda text
            font_kda = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 33)

            kda_text_w, kda_text_h = self.bot.transposer.get_text_wh(self.kda, font_kda)
            draw.text((0, height - kda_text_h - information_height - ability_h), self.kda, font=font_kda, align="right")

            # outcome text
            outcome_text_w, outcome_text_h = self.bot.transposer.get_text_wh(self.outcome, font_kda)
            colour_dict = {
                "Win": str(const.MaterialPalette.green(shade=800)),
                "Loss": str(const.MaterialPalette.red(shade=900)),
                "Not Scored": (255, 255, 255),
            }
            draw.text(
                xy=(0, height - kda_text_h - outcome_text_h - information_height - ability_h),
                text=self.outcome,
                font=font_kda,
                align="center",
                fill=colour_dict[self.outcome],
            )

            # img.show()
            return img

        return await asyncio.to_thread(build_notification_image)
