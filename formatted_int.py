from math import floor

def formatInt(number: int) -> str:
    if number < 1000:
        return f"{number}"
    if number < 1000000:
        return f"{round(floor(number/100)/10, 1)}K"
    if number < 1000000000:
        return f"{round(floor(number/100000)/10, 1)}M"
    return f"{round(floor(number/100000000)/10, 1)}B"

def fullFormatInt(number: int) -> str:
    modified = str(number)[::-1]
    res = ""

    for index in range(len(modified)):
        if not index%3 and index > 0:
            res += ","
        res += modified[index]

    return res[::-1]