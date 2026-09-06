"""Validation and normalization rules for market identifiers."""


def is_valid_isin(value: str) -> bool:
    """Validate an ISO 6166 ISIN, including its Luhn check digit."""
    value = value.strip().upper()
    if len(value) != 12 or not value[:2].isalpha() or not value[2:].isalnum():
        return False
    digits = "".join(
        str(ord(character) - ord("A") + 10) if character.isalpha() else character
        for character in value
    )
    total = 0
    for index, character in enumerate(reversed(digits)):
        number = int(character)
        if index % 2:
            number *= 2
        total += number // 10 + number % 10
    return total % 10 == 0


def is_valid_cusip(value: str) -> bool:
    """Validate a nine-character CUSIP, including its check digit."""
    value = value.strip().upper()
    if len(value) != 9 or not value.isalnum():
        return False
    total = 0
    for index, character in enumerate(value[:8]):
        number = int(character) if character.isdigit() else ord(character) - 55
        if index % 2:
            number *= 2
        total += number // 10 + number % 10
    return (10 - total % 10) % 10 == int(value[-1])


def us_cusip(value: str) -> str | None:
    """Return the CUSIP represented by a US ISIN or a direct CUSIP."""
    value = value.strip().upper()
    if is_valid_cusip(value):
        return value
    if value.startswith("US") and is_valid_isin(value):
        cusip = value[2:11]
        return cusip if is_valid_cusip(cusip) else None
    return None
