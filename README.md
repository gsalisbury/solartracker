# Raspberry Pi solar panel actuator controller

Solar panel tracking program to maximise the sunlight gathered during a day
from a set of solar panels driven by linear actuators. Designed to run on a Raspberry
Pi and uses the GPIO pins to control a set of relays (2 for each actuator) which apply
power to the linear actuators for driving the panels east or west.

The solar panels are mounted on north-south aligned axles, each with a linear
actuator for driving the panels east to west during the day following the sun's
movement across the sky. Actuators used are 36" Superjack linear actuators, commonly
used for satellite dish tracking.

The PyEphem library is used to calculate the sunrise and sunset times for the current day
based on the local latitude and longitude, and relies on the local time on the Raspberry Pi
being correct.
