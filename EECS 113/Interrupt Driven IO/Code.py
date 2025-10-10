import RPi.GPIO as GPIO
import time

#GPIO button-pin assignments
binary_buttons = [25, 18, 27]
leds = [5, 6, 12]
pwm_led = 13
increment_button = 22
decrement_button = 23

GPIO.setmode(GPIO.BCM)        #use BCM pin numbering (GPIO numbers)
GPIO.setwarnings(False)        #disable GPIO warnings

#set up each LED as output and to off
for i in leds:
    GPIO.setup(i, GPIO.OUT)
    GPIO.output(i, GPIO.LOW)

#init PWM LED as output and start at 0% frequency
GPIO.setup(pwm_led, GPIO.OUT)
pwm = GPIO.PWM(pwm_led, 1000)
pwm.start(0)

#init all buttons as pullup resistors
for button in binary_buttons:
    GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

GPIO.setup(increment_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(decrement_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#global value used for tracking
current_value = 0

#update LEDs and PWM given the current value as argument
def update_leds(value):
    binary_value = f"{value:03b}"        #get binary of decimal value

    #turn on LED if bit is 1, else turn it off
    for bit in range(3):
        if binary_value[bit] == '1':
            GPIO.output(leds[bit], GPIO.HIGH)
        else:
            GPIO.output(leds[bit], GPIO.LOW)

    #change pwm frequency base on current value
    pwm.ChangeDutyCycle(value*14.285)    #100%/7=14.285%

#ISR for binary representation buttons
def button_press(channel):
    global current_value
    time.sleep(0.08)     #debounce at 80ms
    new_value = 0

    #get decimal number based on button press(es)
    for i, button in enumerate(binary_buttons):
        if GPIO.input(button) == GPIO.LOW:    #pressed=LOW
            x = pow(2, i)            #index/bit gives value
            new_value+= x            #accumulate each bit value
            
    current_value = new_value
    print('Current value: ', current_value)
    binary_value = f"{current_value:03b}"
    print('Current binary: ', binary_value)
    update_leds(current_value)            #update leds based on new value
    
    
#ISR for increment button
def increment(channel):
    print("Incrementing...")
    global current_value
    time.sleep(0.05)                #debounce at 50ms
    current_value = (current_value + 1) % 8        #wrap around to 0 if above 7
    
    #print to lcd the new incremented value
    print('Current decimal: ', current_value)
    binary_value = f"{current_value:03b}"
    print('Current binary: ', binary_value)
    
    update_leds(current_value)            #update leds based on new value


#ISR for decrement button
def decrement(channel):
    print("Decrementing...")
    global current_value
    time.sleep(0.05)                #debounce at 50ms
    current_value = (current_value - 1) % 8        #wrap around to 7 if below 0
    
    #print to lcd the new incremented value
    print('Current decimal: ', current_value)
    binary_value = f"{current_value:03b}"
    print('Current binary: ', binary_value)
    
    update_leds(current_value)            #update leds based on new value

#init interrupt
'''if button is pressed, button_press is called, debounces and ignore other
edges for 300ms'''
for button in binary_buttons:
    GPIO.add_event_detect(button, GPIO.FALLING, callback=button_press, bouncetime=300)

#increment/decrement if button is pressed, debounces for 300ms too
GPIO.add_event_detect(increment_button, GPIO.FALLING, callback=increment, bouncetime=300)
GPIO.add_event_detect(decrement_button, GPIO.FALLING, callback=decrement, bouncetime=300)


#run program
try:
    while True:
        time.sleep(1)    #run forever
finally:
    pwm.stop()        #stop pwm
    GPIO.cleanup()        #reset all GPIO settings
