def picture_percent(value, previous):
    kept = _whole(previous)
    if kept is None:
        kept = 20
    if value is None:
        return kept
    if isinstance(value, str) and not value.strip():
        return kept
    number = _whole(value)
    if number is None or number < 10 or number > 40:
        return kept
    return number


def _whole(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
    elif isinstance(value, (int, float)):
        number = float(value)
    else:
        return None
    if number != int(number):
        return None
    return int(number)
