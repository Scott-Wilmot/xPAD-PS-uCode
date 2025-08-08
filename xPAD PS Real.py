"""
Potential future changes/fixes:
    - The while loop in the main function remains running forever even when the signal hasn't been detefcted and the led is blinking (If loop timer is set to a very large value it typically consumes little to no room)
"""
from machine import Pin, Timer
import uasyncio as aio

#//////////
# Variables
#//////////
com_pin = Pin(3, mode=Pin.IN) # Pin attached to the RS485 input
led_pin = Pin(12, mode=Pin.OUT) # Failure LED pin
hardware_enable_pin = Pin(21, mode=Pin.OUT) # Pin connected to the ULN2003 for enabling the meerstetter GPIO

flag = aio.ThreadSafeFlag() # Acts as an execution blocking object until the flag is set (see first_signal())
event_loop = aio.new_event_loop()

timer = Timer()
timer_period_ms = 5000 # The time in milliseconds between checks for a received signal by the timer
ping = False # Acts as the state check for if any signal has been recieved in the past timer window


#////////////////////////////
# Setup and Cleanup Functions 
#////////////////////////////

def setup():
    com_pin.irq(handler=first_signal, trigger=Pin.IRQ_RISING, hard=True)


def cleanup():
    # Set all OUT pins to the off state as default
    led_pin.off()
    hardware_enable_pin.off()
    
    # Disable Timer
    timer.deinit()


#//////////
# Functions
#//////////

"""
Function handles the first recieved signal from the serial port
    and changes com ports behavior for further signals
"""
def first_signal(_):
    print("First signal received!")
    flag.set()
    hardware_enable_pin.on()
    com_pin.irq(handler=refresh_handler, trigger=Pin.IRQ_RISING, hard=True)
    
    global ping
    ping = True # Defaulting true after first signal gives lenience for first cycle, false is stricter requiring another signal before the timer ends
    hardware_enable_pin.on() # Questionable if this should go here or in the startup function, check with Yoram


"""
Handler function for when the serial port transmits data to the computer

Sets the ping variable to true to represent a signal within the last time check window
"""
def refresh_handler(_):
    print("Refresh received")
    com_pin.irq(handler=None)
    global ping
    ping = True


"""
Simple code for infinitely blinking the light once the no signal error has been detected

This code represents the end state of the program, only action to do from here is reboot the power
"""
async def connection_disconnect():
    print("Disconnect...end of program")
    while True:
        led_pin.on()
        await aio.sleep(0.1)
        led_pin.off()
        await aio.sleep(0.1)
        led_pin.on()
        await aio.sleep(0.1)
        led_pin.off()
        await aio.sleep(0.5)


"""
Handler function for the activity timer

Checks if a signal has been recieved from the serial port within the last time window
"""
def timer_handler(_):
    global ping
    
    # Yes activity case
    if ping:
        ping = False
        com_pin.irq(handler=refresh_handler, trigger=Pin.IRQ_RISING, hard=True)
    # No activity
    else:
        # Disable relevant activities
        timer.deinit()
        hardware_enable_pin.off()
        com_pin.irq(handler=None)
        aio.run(connection_disconnect())


#////////////////
# Main event loop
#////////////////
async def main():
    setup()
    
    await flag.wait() # Blocks execution until com_pin is first triggered
    
    timer.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=timer_handler) # Start the listening loop for any received signals
    
    # Sleep loop is required to prevent the method from ending so the timer can run forever (or until the signal is not recieved)
    while True:
        await aio.sleep(1000) # Arbitrary long wait time to prevent the loop from consuming a bunch of resources


#//////////////
# Executed code
#//////////////
try:
    aio.run(main())
    event_loop.run_forever()
finally:
    cleanup()
