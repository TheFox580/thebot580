import mcci

mcci_stats_fox = mcci.getMCCIInfo("TheFox580")
print(mcci_stats_fox.saveAsJSON())