from enum import Enum


class EnumID(Enum):
    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return self.mention

    @property
    def id(self):
        return self.value

    @property
    def mention(self) -> str:
        raise NotImplemented


class ChannelEnum(EnumID):
    @property
    def mention(self) -> str:
        return f'<#{self.value}>'


class RoleEnum(EnumID):
    @property
    def mention(self) -> str:
        return f'<@&{self.value}>'


class UserEnum(EnumID):
    @property
    def mention(self) -> str:
        return f'<@{self.value}>'
