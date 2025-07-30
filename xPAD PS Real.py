from machine import Pin, Timer
import uasyncio as aio
import sys


#//////////
# Variables
#//////////
com_pin = Pin(3, mode=Pin.IN)
led_pin = Pin(12, mode=Pin.OUT)
hardware_enable_pin = Pin(21, mode=Pin.OUT)

flag = aio.ThreadSafeFlag()
event_loop = aio.new_event_loop()

timer = Timer()

task_list = []

ping = None


#////////////////////////////
# Setup and Cleanup Functions 
#////////////////////////////

def setup():
    com_pin.irq(handler=first_signal, trigger=Pin.IRQ_RISING)


def cleanup():
    # Set all OUT pins to the off state as default
    led_pin.off()
    hardware_enable_pin.off()
    
    # Disable Timer
    timer.deinit()
    
    # Kill all active tasks
    for task in task_list:
        try:
            task.cancel()
        except BaseException as e:
            print(e)


#//////////
# Functions
#//////////

def first_signal(_):
    flag.set()
    hardware_enable_pin.on()
    com_pin.irq(handler=refresh_signal, trigger=Pin.IRQ_RISING, hard=True)
    ping = True # Defaulting true after first signal gives lenience for first cycle, false is stricter requiring another signal before the timer ends
    

def refresh_signal(_):
    print("Refresh received!")
    com_pin.irq(handler=None)
    global ping
    ping = True


async def connection_disconnect():
    while True:
        led_pin.on()
        await aio.sleep(0.1)
        led_pin.off()
        await aio.sleep(0.1)
        led_pin.on()
        await aio.sleep(0.1)
        led_pin.off()
        await aio.sleep(0.5)


def timer_callback(_):
    global ping
    
    # Yes activity case
    if ping:
        ping = False
        com_pin.irq(handler=refresh_signal, trigger=Pin.IRQ_RISING, hard=True)
    # No activity
    else:
        # Disable relevant activities
        timer.deinit()
        com_pin.irq(handler=None)
        aio.run(connection_disconnect())


#////////////////
# Main event loop
#////////////////
async def main():
    setup()
    
    await flag.wait() # Blocks execution until com_pin is first triggered
    
    timer.init(mode=Timer.PERIODIC, period=5000, callback=timer_callback) # Start the listening loop for any received signals
    
    while True:
        await aio.sleep(5)


#//////////////
# Executed code
#//////////////
try:
    aio.run(main())
    event_loop.run_forever()
except BaseException as e:
    print(f'RUN ERROR: {e}')
finally:
    cleanup()
