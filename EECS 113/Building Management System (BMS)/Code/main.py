import RPi.GPIO as GPIO
import time
from datetime import datetime
import LCD1602 as lcd1602
import Freenove_DHT as DHT
import requests, json

# setup mode
GPIO.setmode(GPIO.BCM)


# init everything
def init_everything():
    global lcd
    global pir_sensor
    global lights_led, lights_on, last_time_triggered
    global security_button, security_enabled
    global url, response, x, humidity
    global hvac_off, heat, ac, dht_pin, dht, temp_list, weather_index
    global inc_temp, dec_temp, desired_temp
    global ac_led, heater_led
    global fire_alarm
    global logfile

    # lcd
    lcd = lcd1602.CharLCD1602()
    lcd.init_lcd()
    lcd.clear()

    # init pir sensor
    pir_sensor = 5  # pir sensor, random pin assignment
    GPIO.setup(pir_sensor, GPIO.IN)

    # init lights led
    lights_led = 16  # Lights LED, random pin assignment
    GPIO.setup(lights_led, GPIO.OUT)
    GPIO.output(lights_led, GPIO.LOW)
    lights_on = False
    last_time_triggered = time.time()

    # init security system
    security_button = 23  # door/window button , random pin
    GPIO.setup(security_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    security_enabled = True

    # init api system
    url = "http://api.openweathermap.org/data/2.5/weather?q=Irvine,US&appid=bf323aef8f185b426b5edec1cf1d211c"
    response = requests.get(url).json()
    x = response["main"]
    humidity = x["humidity"]

    # init hvac system
    hvac_off = True
    heat = False
    ac = False
    dht_pin = 17  # temp pin assignment
    GPIO.setup(dht_pin, GPIO.IN)
    dht = DHT.DHT(dht_pin)
    temp_list = []
    while len(temp_list) < 3:  # append three readings for first temperature
        for i in range(0, 15):
            chk = dht.readDHT11()
            if (chk == 0):
                break
            time.sleep(0.1)
        temp_now = dht.getTemperature()
        temp_list.append(temp_now)
        time.sleep(1)
    t = sum(temp_list) / 3
    t = int((t * 1.8) + 32)
    weather_index = round(t + 0.05 * humidity)  # init weather_index as 0
    desired_temp = weather_index  # init desired_temp as 69

    # init buttons for hvac
    inc_temp = 14  # temp pin assignment
    dec_temp = 18  # temp pin assignment
    GPIO.setup(inc_temp, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(dec_temp, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # init leds for hvac
    ac_led = 25  # temp pin assignment
    heater_led = 12  # temp pin assignment
    GPIO.setup(ac_led, GPIO.OUT)
    GPIO.output(ac_led, GPIO.LOW)
    GPIO.setup(heater_led, GPIO.OUT)
    GPIO.output(heater_led, GPIO.LOW)

    # init fire alarm system
    fire_alarm = False

    # open log file
    logfile = open('log.txt', 'w')


# ----------------------------------------------- helper functions ——------------------------------------------------#

# fire alarm flash
def flash_leds():
    GPIO.output(lights_led, GPIO.HIGH)
    GPIO.output(ac_led, GPIO.HIGH)
    GPIO.output(heater_led, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(lights_led, GPIO.LOW)
    GPIO.output(ac_led, GPIO.LOW)
    GPIO.output(heater_led, GPIO.LOW)
    time.sleep(0.5)


# get ambient temperature
def get_temp():
    for i in range(0, 15):
        chk = dht.readDHT11()
        if (chk == 0):
            break
        time.sleep(0.1)
    temp_now = dht.getTemperature()
    temp_list.append(temp_now)
    if len(temp_list) > 3:
        temp_list.pop(0)
    temp = sum(temp_list) / 3
    return int((temp * 1.8) + 32)  # convert to fahrenheit


# change desired temperature
def change_desired_temp():
    global desired_temp
    if GPIO.input(inc_temp) == GPIO.LOW and desired_temp < 95:
        desired_temp += 1
        return
    if GPIO.input(dec_temp) == GPIO.LOW and desired_temp > 65:
        desired_temp -= 1
        return


# turn on heater
def turn_on_heater():
    global heat, ac, hvac_off
    heat = True
    log_event('HVAC HEAT')
    ac = False
    GPIO.output(ac_led, GPIO.LOW)  # turn off ac led if on
    hvac_off = False
    lcd.clear()
    lcd.write(5, 0, 'HEATER')  # display message
    lcd.write(7, 1, 'ON')
    GPIO.output(heater_led, GPIO.HIGH)  # turn on heater led
    time.sleep(3)
    lcd.clear()
    return

# turn on ac
def turn_on_ac():
    global heat, ac, hvac_off
    heat = False
    GPIO.output(heater_led, GPIO.LOW)  # turn off heater led if on
    ac = True
    log_event('HVAC AC')
    hvac_off = False
    lcd.clear()
    lcd.write(7, 0, 'AC')  # display message
    lcd.write(7, 1, 'ON')
    GPIO.output(ac_led, GPIO.HIGH)  # turn on ac led
    time.sleep(3)
    lcd.clear()
    return


# turn off hvac
def turn_off_hvac():
    global heat, ac, hvac_off
    heat = False
    ac = False
    hvac_off = True
    log_event('HVAC OFF')
    GPIO.output(heater_led, GPIO.LOW)  # turn off heater led
    GPIO.output(ac_led, GPIO.LOW)  # turn off ac led
    time.sleep(0.3)
    return

# turn on hvac
def turn_on_hvac():
    # turn on heat or ac
    if weather_index <= desired_temp - 3:
        turn_on_heater()
    else:
        if weather_index >= desired_temp + 3:
            turn_on_ac()


# save logs to file
def log_event(event):
    global logfile
    timestamp = datetime.now().strftime('%H:%M:%S')
    logfile.write(f"{timestamp} {event}\n")
    logfile.flush()


# -------------------------------------------------- run systems —--—------------------------------------------------#

# run PIR sensor + ambient light control system
def run_pir_sensor():
    global lights_on, last_time_triggered, pir_sensor, lights_led
    # motion detected
    if GPIO.input(pir_sensor):
        log_event('MOTION DETECTED')
        timestamp = datetime.now().strftime('%H:%M:%S')
        print("motion detected at: ", timestamp)
        # if lights not on, turn it on
        if not lights_on:
            GPIO.output(lights_led, GPIO.HIGH)  # turn on lights led
            lights_on = True
            log_event('LIGHTS ON')
        last_time_triggered = time.time()
    # no motion detected
    else:
        # if lights on, check if it has been > 10 secs
        if lights_on and (time.time() - last_time_triggered >= 10):
            GPIO.output(lights_led, GPIO.LOW)  # turn off lights led
            lights_on = False
            log_event('LIGHTS OFF')
        # if lights off or has not been > 10 secs, continue
    # time.sleep(0.3)


# run fire alarm system
def run_fire_alarm():
    global fire_alarm, security_enabled, weather_index
    fire_alarm = True
    log_event('FIRE ALARM ON')

    # open window/door
    lcd.clear()
    security_enabled = False
    log_event('DOOR OPEN')
    log_event('HVAC OFF')
    lcd.write(1, 0, 'Window/Door  O')
    lcd.write(2, 1, 'HVAC  HALTED')
    turn_off_hvac()
    time.sleep(3)  # display for 3 seconds

    # display emergency message
    lcd.clear()
    lcd.write(3, 0, 'FIRE! Dr: O')
    lcd.write(0, 1, 'Please evacuate!')

    # flashes leds
    while fire_alarm:
        flash_leds()
        ct = get_temp()
        weather_index = round(ct + 0.05 * humidity)
        if weather_index < 95:
            fire_alarm = False
            lcd.clear()
            lcd.write(0, 0, 'Resuming normal')
            lcd.write(1, 1, 'operations...')
            time.sleep(3)
    # resume normal operations
    log_event('FIRE ALARM OFF')
    lcd.clear()
    return


# run security system
def run_security():
    global security_enabled, security_button, lcd
    # button pressed
    if GPIO.input(security_button) == GPIO.LOW:
        # open/close door/window, turn on/off HVAC
        security_enabled = not security_enabled
        lcd.clear()

        # if door/window open, turn off HVAC
        if not security_enabled:
            log_event('DOOR OPEN')
            log_event('HVAC OFF')
            lcd.write(1, 0, 'Window/Door  O')
            lcd.write(2, 1, 'HVAC  HALTED')
            time.sleep(3)  # display for 3 seconds
            turn_off_hvac()
            lcd.clear()
            return
        else:
            log_event('DOOR CLOSED')
            lcd.write(1, 0, 'Window/Door  C')
            lcd.write(4, 1, 'HVAC  ON')
            time.sleep(3)  # display for 3 seconds
            turn_on_hvac()
            lcd.clear()
            return

    # time.sleep(0.2)


# run temperature control system
def run_hvac():
    global heat, ac, weather_index, desired_temp, security_enabled
    # listen for desired temp change and turn on/off hvac accordingly
    change_desired_temp()
    # time.sleep(0.5)
    if (weather_index <= desired_temp - 3) and not heat and security_enabled:
        turn_on_heater()
    else:
        if (weather_index >= desired_temp + 3) and not ac and security_enabled:
            turn_on_ac()



# display all statuses
def display_statuses():
    global weather_index, humidity, desired_temp
    # lights status
    if lights_on:
        lcd.write(12, 1, 'L:ON')
    else:
        lcd.write(11, 1, 'L:OFF')
    # window/door status
    if not security_enabled:
        lcd.write(12, 0, 'Dr:O')
    else:
        lcd.write(12, 0, 'Dr:C')

    # hvac status
    if hvac_off:
        lcd.write(0, 1, 'H:OFF')
    elif heat:
        lcd.write(0, 1, 'H:HEAT')
    elif ac:
        lcd.write(0, 1, 'H:AC')
    else:
        lcd.write(0, 1, 'H:ERR')  #fallback

    # update temps
    current_temp = get_temp()
    weather_index = round(current_temp + 0.05 * humidity)
    lcd.write(0, 0, str(desired_temp))
    lcd.write(2, 0, "/" + str(weather_index))

    #update time
    timestamp = datetime.now().strftime('%H:%M')
    lcd.write(7, 0, timestamp)


# main function (needs to run updated temp/listen for button presses/watch for fire, etc.)
def main():
    init_everything()
    global weather_index, humidity, desired_temp, temp_list
    while True:
        lcd.clear()
        if weather_index >= 95:
            run_fire_alarm()
        run_pir_sensor()
        run_security()
        run_hvac()
        display_statuses()
        time.sleep(0.5)

try:
    main()
finally:
    global logfile
    logfile.close()
    lcd.clear()
    GPIO.cleanup()
