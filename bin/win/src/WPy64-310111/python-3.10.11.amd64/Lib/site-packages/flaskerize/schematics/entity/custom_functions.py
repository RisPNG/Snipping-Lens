from flaskerize import register_custom_function


@register_custom_function
def capitalize(val: str) -> str:
    return val.capitalize()


@register_custom_function
def lower(val: str) -> str:
    return val.lower()
