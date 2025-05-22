import rstr

def generate_random_value(regex: str = None):
    if regex:
        try:
            return rstr.xeger(regex)
        except Exception:
            # fallback if regex invalid
            return "invalid_regex"
    from random import choices
    import string
    return ''.join(choices(string.ascii_letters + string.digits, k=8))
