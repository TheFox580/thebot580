def roundToNNearest(time: int, n: int):
    time = round(time/n)
    return time*n

print(roundToNNearest(2*60+44, 60))
