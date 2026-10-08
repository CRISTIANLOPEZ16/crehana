from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


TRIM_EXPRESSION = " || ".join(
    f"chr({codepoint})"
    for codepoint in (
        *[codepoint for codepoint in range(128) if chr(codepoint).isspace()],
        0x85,
        0xA0,
        0x1680,
        *range(0x2000, 0x200B),
        0x2028,
        0x2029,
        0x202F,
        0x205F,
        0x3000,
    )
)
