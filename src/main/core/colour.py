from discord import Colour


class ZColour(Colour):
    @classmethod
    def rounded(cls):
        return cls(0x2F3136)

    @classmethod
    def me(cls):
        return cls(0x3DB4FF)
