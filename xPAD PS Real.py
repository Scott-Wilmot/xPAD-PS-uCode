from machine import Pin, Timer
import uasyncio as aio
import sys


#//////////
# Variables
#//////////
com_pin = Pin(0, mode=Pin.IN)
test_pin = Pin(25, mode=Pin.OUT)
error_pin = Pin(2, mode=Pin.OUT)
hardware_enable_pin = Pin(6, mode=Pin.OUT)

flag = aio.ThreadSafeFlag()
event_loop = aio.new_event_loop()

timer = Timer()

task_list = []


#////////////////////////////
# Setup and Cleanup Functions 
#////////////////////////////
async def setup():
    test_pin.irq(handler=first_signal, trigger=Pin.IRQ_RISING)


def cleanup():
    # Set all OUT pins to the off state as default
    test_pin.off()
    error_pin.off()
    hardware_enable_pin.off()
    
    # Disable Timer
    timer.deinit()
    
    # Kill all active tasks
    for task in task_list:
        try:
            task.cancel()
        except BaseException as e:
            print(e)

#///////////////////////
# "Artificial" Functions
#///////////////////////
async def artificial_break():
    await aio.sleep(0.5)
    test_pin.on()
        
        
async def artificial_loop():
        while True:
            test_pin.on()
            await aio.sleep(1)
            test_pin.off()
            await aio.sleep(1)
            

#/////////////////
# "Real" Functions
#/////////////////
def first_signal(_):
    print("Init active")
    flag.set()
    hardware_enable_pin.on()
    

def refresh_signal(_):
    if 'ping' in globals():
        global ping
        ping = True
        test_pin.irq(handler=None)
#         print("Disabling pin irq...")
    else:
        print("ping not in global scope")


async def connection_disconnect():
    try:
        task_list[-1].cancel()
    except BaseException as e:
        print(f'CANCEL ERROR: {e}')
    except Exception:
        print("Random ah error")
    
    
    while True:
        error_pin.on()
        await aio.sleep(0.1)
        error_pin.off()
        await aio.sleep(0.1)
        error_pin.on()
        await aio.sleep(0.1)
        error_pin.off()
        await aio.sleep(0.5)


def timer_callback(_):
    global ping
    
    try:
        # Yes activity case
        if ping:
            ping = False
            test_pin.irq(handler=refresh_signal, trigger=Pin.IRQ_RISING)
        # No activity
        else:
            # Disable relevant activities
            timer.deinit()
            print("DEAD")
            aio.run(connection_disconnect())
            
            
    # Uninitialized Case    
    except Exception as e:
        print(f'ERROR: {type(e)}')
        ping = False
        
        
async def idle():
    aio.create_task(artificial_break()) # This simulates activity, when attached to the assembly this would be removed entirely
    await flag.wait()
    test_pin.off()
    
    
async def listening_loop():
    test_pin.irq(handler=refresh_signal, trigger=Pin.IRQ_RISING)
    timer.init(mode=Timer.PERIODIC, period=1500, callback=timer_callback)
    
    a_task = aio.create_task(artificial_loop())
    task_list.append(a_task)


#////////////////
# Main event loop
#////////////////
async def main():
    await aio.create_task(setup())

    task = aio.create_task(idle())
    task_list.append(task)
    await task
    
    # Initial communication received, change COM pin timer_callback behavior
    task = aio.create_task(listening_loop())
    task_list.append(task)
    
    event_loop.run_forever()


#//////////////
# Executed code
#//////////////
try:
    aio.run(main())
except BaseException as e:
    print(f'RUN ERROR: {e}')
finally:
    cleanup()
