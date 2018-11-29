#!/usr/bin/env python

"""
Solar panel tracking program.
 
Uses the PyEphem library to calculate the sun's position for the current day,
and uses the resulting sunrise, transit, and sunset times to point the solar
panels towards the sun.

Divides the time between sunrise and sunset into 15 minute chunks, and at the
start of each chunk drives the panels by extending the linear actuators one at
a time.
 
At the end of the day, at sunset, drives the panels back to the east ready for
the next day.
"""

import ephem
from datetime import datetime
import RPi.GPIO as GPIO
import time

# Global variables
relay_cycle_min = 2.25
sunset_linger_time = 7200

# Panel variables
panels = {
  1: {'east_pin': 2, 'west_pin': 3, 'throw_time': 60, 'east_limit_angle': -45, 'west_limit_angle': 45},
  2: {'east_pin': 27, 'west_pin': 22, 'throw_time': 120, 'east_limit_angle': -60, 'west_limit_angle': 60},
  3: {'east_pin': 4, 'west_pin': 17, 'throw_time': 120, 'east_limit_angle': -60, 'west_limit_angle': 60}
}

def get_step_count():
    shortest_throw = 0
    for i in range(1, len(panels) + 1):
        if i == 1:
            shortest_throw = panels[i]['throw_time']
            shortest_throw_panel = i
        elif panels[i]['throw_time'] < shortest_throw:
            shortest_throw = panels[i]['throw_time']
            shortest_throw_panel = i

    # Populate panels dict with step times for each panel
    for i in range(1, len(panels) + 1):
        if i == shortest_throw_panel:
            panels[i]['step_time'] = relay_cycle_min
        else:
            panels[i]['step_time'] = ( panels[i]['throw_time'] / panels[shortest_throw_panel]['throw_time'] ) * relay_cycle_min
    
    # Return the step count for today 
    return shortest_throw / relay_cycle_min

def sun_times():
    # Make an ephem observer for this location
    l = ephem.Observer()
    l.date = datetime.now().strftime('%Y-%m-%d')
    # Note that lat and lon must be in string format
    l.lon  = str(152.585)
    l.lat  = str(-25.939)

    # Elevation in metres
    l.elev = 120

    # Set horizon
    l.horizon  = '10:00'

    sunrise = l.previous_rising(ephem.Sun()) #Sunrise
    noon    = l.next_transit   (ephem.Sun(), start=sunrise) #Solar noon
    sunset  = l.next_setting   (ephem.Sun()) #Sunset

    l_sunrise = ephem.localtime(sunrise)
    l_noon    = ephem.localtime(noon)
    l_sunset  = ephem.localtime(sunset)

    # Return times in unixtime
    return int(l_sunrise.strftime('%s')), int(l_noon.strftime('%s')), int(l_sunset.strftime('%s'))

def log_time():
    return datetime.now().strftime('[ %Y-%m-%d %H:%M:%S ]')

def get_sleep_time(sunrise, sunset):
    return (sunset - sunrise) / get_step_count()

def step_west(steps_done, at_eastern_limit):
    if (steps_done == 0) and not at_eastern_limit:
        goto_eastern_limit()

    for i in range(1, len(panels) + 1):
        print "%s Moving panel %d one step west" % (log_time(), i)
        GPIO.output(panels[i]['west_pin'], GPIO.LOW)
        time.sleep(panels[i]['step_time'])
        GPIO.output(panels[i]['west_pin'], GPIO.HIGH)
        time.sleep(0.25)
    
def goto_eastern_limit():
    for i in range(1, len(panels) + 1):
        print "%s Moving panel %d to the eastern limit" % (log_time(), i)
        GPIO.output(panels[i]['east_pin'], GPIO.LOW)
        time.sleep(panels[i]['throw_time'])
        GPIO.output(panels[i]['east_pin'], GPIO.HIGH)
        time.sleep(0.25)

def goto_western_limit():
    for i in range(1, len(panels) + 1):
        print "%s Moving panel %d to the western limit" % (log_time(), i)
        GPIO.output(panels[i]['west_pin'], GPIO.LOW)
        time.sleep(panels[i]['throw_time'])
        GPIO.output(panels[i]['west_pin'], GPIO.HIGH)
        time.sleep(0.25)

def init_pins():
    print "%s Initialising GPIO pins.." % log_time()

    # Setup GPIO pins
    GPIO.setmode(GPIO.BCM)

    for i in range(1, len(panels) + 1):
        GPIO.setup(panels[i]['east_pin'], GPIO.OUT) 
        GPIO.output(panels[i]['east_pin'], GPIO.HIGH)
        GPIO.setup(panels[i]['west_pin'], GPIO.OUT) 
        GPIO.output(panels[i]['west_pin'], GPIO.HIGH)

def main_loop():
    init_pins()
    at_eastern_limit = True
    at_western_limit = False

    while True:
        # A new day! Get today's day of month and sunrise, noon and sunset times
        print "%s Entering new loop for today." % log_time()
        day_of_month = datetime.now().strftime('%d')
        sunrise, noon, sunset = sun_times()

        # Get the amount of tracking steps needed today
        sleep_time = get_sleep_time(sunrise, sunset)
        steps_done = 0

        # Enter today's loop
        while datetime.now().strftime('%d') == day_of_month:
            loop_time = int(datetime.now().strftime('%s'))

            # If it is before sunrise go back to sleep
            if loop_time < sunrise:
                print "%s It is too early, going back to sleep for %d seconds." % (log_time(), sleep_time)
                time.sleep(sleep_time)
            # Else if past sunrise and before sunset and we're not at the western limit yet, step panels west
            elif loop_time < sunset and not at_western_limit:
                if steps_done < get_step_count():
                    step_west(steps_done, at_eastern_limit)
                    steps_done += 1
                    at_eastern_limit = False
                    print "%s Steps done today: %d" % (log_time(), steps_done)
                else:
                    print "%s Steps (%d) have reached today's count (%d), staying here until past sunset" % (log_time(), steps_done, step_count)
            elif loop_time > sunset and loop_time < (sunset + sunset_linger_time):
                print "%s Waiting until %d hours past sunset before driving panels east, sleeping %d seconds" % (log_time(), (sunset_linger_time / 3600), sleep_time)
            elif loop_time > (sunset + sunset_linger_time):
                if not at_eastern_limit: 
                    print "%s Now %d hours past sunset, readying for the next day by driving panels east." % (log_time(), (sunset_linger_time / 3600))
                    goto_eastern_limit()
                    at_eastern_limit = True
                else:
                    print "%s Past sunset and ready for the morning, sleeping for %d seconds" % (log_time(), sleep_time)

            time.sleep(sleep_time)


if __name__ == "__main__":
    try:
        main_loop()
    except Exception as e:
        print "%s Exception dump: %s : %s." % (log_time(), type(e).__name__, e)

    finally:
        # Reset GPIO settings on exit
        GPIO.cleanup()
