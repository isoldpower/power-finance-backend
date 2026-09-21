from enum import IntEnum, StrEnum


class FieldSettings(IntEnum):
    MAX_NAME_LENGTH = 120
    MAX_ICON_LENGTH = 64


class HelpText(StrEnum):
    TARGET = "The amount the goal is saving towards, as a flat decimal string taking its currency from the goal. A money object in the response, a bare string here — the same asymmetry POST /transactions uses."
    PROGRESS = "Ignored if sent. Progress is derived from the transactions touching the goal, the same way a wallet's balance is, and no endpoint writes it."
    AMOUNT = 'Decimal string, e.g. "50.00". Always a positive magnitude — direction is `type`. Fewer fraction digits than the currency\'s scale are zero-padded; more are rejected.'
    COLOR = "CSS hex colour, #RGB / #RRGGBB / #RRGGBBAA."
    ZERO_BALANCE = "The point the balance is measured from, as a flat decimal string taking its currency from the wallet. Not a floor: the balance may go below it, and what the user owns is the difference."
    OPENING_BALANCE = "What the wallet already held, as a flat decimal string. Recorded as an opening transaction, not stored on the wallet, so it is never echoed back. Defaults to `zero_balance`, which opens the wallet owning nothing."


HEX_COLOR = "^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$"
