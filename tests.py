import mcci

data = mcci.getMCCIInfo("DarkZorua")

print(f"Total Playtime on MCCI for {data.getUsername()}:")
print(data.getStatistic("playtime") / 20, "seconds")
print(data.getStatistic("playtime") / 20/60, "mins")
print(data.getStatistic("playtime") / 20/60/60, "hours")
print(data.getStatistic("playtime") / 20/60/60/24, "days")
print(data.getStatistic("playtime") / 20/60/60/24/7, "weeks")
print(data.getStatistic("playtime") / 20/60/60/24/365.25 * 12, "months")
print(data.getStatistic("playtime") / 20/60/60/24/365.25, "years")
