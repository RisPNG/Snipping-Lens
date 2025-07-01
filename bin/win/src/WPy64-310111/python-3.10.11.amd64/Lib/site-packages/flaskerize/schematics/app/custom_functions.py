from flaskerize import register_custom_function


@register_custom_function
def derp_case(val: str) -> str:
    from itertools import zip_longest

    ups = val[::2].upper()
    downs = val[1::2].lower()
    result = ""
    for i, j in zip_longest(ups, downs):
        if i is not None:
            result += i
        if j is not None:
            result += j
    return result

