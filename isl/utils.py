import re

_NON_ALNUM = re.compile(r"[^a-z0-9]")


def normalize(text: str) -> str:
    """Collapse text to a lowercase alphanumeric-only key so 'Thank you' and
    'Thankyou.mp4' resolve to the same lookup key."""
    return _NON_ALNUM.sub("", text.lower())
