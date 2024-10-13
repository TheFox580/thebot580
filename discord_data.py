from datetime import datetime, timedelta, timezone
import dateutil.parser
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import csv
import os

yourNameHere = "@thefox580"

dates = []

for dir in os.listdir("."):
	if (os.path.isdir(dir)):
		print(f"reading messages for channel: {dir}")
		with open(dir + '/messages.csv', 'r') as csv_file:
			reader = csv.reader(csv_file)
			for row in reader:
				if (row[1] != "Timestamp"):
					dates.append(dateutil.parser.parse(row[1]))
			csv_file.close()
					
print(f"total messages: {len(dates)}")

renderHorizontal = True
beginningOfTime = datetime.utcnow()-timedelta(days=7*365) # ignore tweets older than 5 years
now = datetime.utcnow()

days=[]
times=[]

print("processing dates")
for date in dates:
	timeNoDate = datetime(1970, 1, 1, date.hour, date.minute, date.second)
	dateNoTime = datetime(date.year, date.month, date.day)
	days.append(dateNoTime)
	times.append(timeNoDate)

print("processing graph")
hoursMajorLocator = mdates.HourLocator(interval=6)
hoursMinorLocator = mdates.HourLocator(interval=1)
hoursMajorFormatter = mdates.DateFormatter('%H:%M')
daysMajorLocator = mdates.YearLocator(base=1)
daysMinorLocator = mdates.MonthLocator()
daysMajorFormatter = mdates.DateFormatter('%Y')
daysMinorFormatter = mdates.DateFormatter('%b')

if renderHorizontal:
	fig, ax = plt.subplots(figsize=((max(days)-min(days)).days / 200, 3))
	plt.scatter(days, times, s=1, linewidths=0, color='#1f77b4c0')
	plt.xlim(min(days), max(days))
	plt.ylim(0, 1)
	dateAxis = ax.xaxis
	hoursAxis = ax.yaxis
	daysMinorFormatter = mdates.DateFormatter('')
else:
	fig, ax = plt.subplots(figsize=(3, (max(days)-min(days)).days / 200))
	plt.scatter(times, days, s=1, linewidths=0, color='#1f77b4c0')
	plt.ylim(min(days), max(days))
	plt.xlim(0, 1)
	dateAxis = ax.yaxis
	hoursAxis = ax.xaxis
	ax.tick_params(axis='y', which='minor', labelsize=5, color='#777')

# time goes downwards and to the right
plt.gca().invert_yaxis()

hoursAxis.set_major_locator(hoursMajorLocator)
hoursAxis.set_minor_locator(hoursMinorLocator)
hoursAxis.set_major_formatter(hoursMajorFormatter)

dateAxis.set_major_locator(daysMajorLocator)
dateAxis.set_minor_locator(daysMinorLocator)
dateAxis.set_major_formatter(daysMajorFormatter)
dateAxis.set_minor_formatter(daysMinorFormatter)

hoursAxis.set_label('Time of day')
dateAxis.set_label('Date')
plt.title(f"When does {yourNameHere} post on Discord (UTC)")

print("rendering png")
plt.savefig('out.png', bbox_inches='tight', pad_inches=0.3, dpi=300)
print("rendering svg")
plt.savefig('out.svg', bbox_inches='tight', pad_inches=0.3)