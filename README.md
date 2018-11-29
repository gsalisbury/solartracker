# solartracker

Solar panel tracking program.

Uses the PyEphem library to calculate the sun's position for the current day,
and uses the resulting sunrise, transit, and sunset times to point the solar
panels towards the sun.

Divides the time between sunrise and sunset into 15 minute chunks, and at the
start of each chunk drives the panels by extending the linear actuators one at
a time.

At the end of the day, an hour after sunset, drives the panels back to the east ready for
the next day.
