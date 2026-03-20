import struct
import time
import sys
import os

i = 0
j = 0
brightness_change = 0
infile_path = "/dev/input/event0"
FORMAT = 'llHHI'

def det_touch():

    global i
    global j
    global brightness_change

    global infile_path

    global FORMAT


    EVENT_SIZE = struct.calcsize(FORMAT)

    # open file in binary mode

    in_file = open(infile_path, "rb")

    time.sleep(0.1)

    os.set_blocking(in_file.fileno(), False)


    event = in_file.read(EVENT_SIZE)

    code = 0
    value = 0
    if not event:
        #print("file is empty")
        brightness_change = 0
    while event:

        (tv_sec, tv_usec, type, code, value) = struct.unpack(FORMAT, event)


        if type != 0 or code != 0 or value != 0:
            #print("********************************************************************************************************")
            #print("Event type %u, code %u, value %u at %d.%d" % \
              #(type, code, value, tv_sec, tv_usec))
            time.sleep(0.05)
            if (code == 57):
                i = i + 1
                #brightness_change = 2
                time.sleep(0.1)
            if (((i >= 1) and (code == 53) and (value >= 600)) or ((i >= 1) and (code == 330))):
                brightness_change = 2
                time.sleep(0.1)
                in_file.close()
                event = ''
                return brightness_change
            elif (i >= 1) and (brightness_change != 2):
                #time.sleep(0.1)
                if (brightness_change == 1):
                    time.sleep(0.05)
                    in_file.close()
                    event = ''
                    return brightness_change
                else:
                    brightness_change = 1
                    time.sleep(0.05)
            elif ((brightness_change != 2) and (brightness_change != 1)):
                time.sleep(0.05)
                brightness_change = 0
                in_file.close()
                event = ''
                return brightness_change

            event = in_file.read(EVENT_SIZE)
            time.sleep(0.1)

        else:
            in_file.close()
            in_file = open(infile_path, "rb")
            os.set_blocking(in_file.fileno(), False)
            event = in_file.read(EVENT_SIZE)

    if (brightness_change == 2):
        in_file.close()
        return 2
    elif brightness_change == 1:
        in_file.close()
        return 1
    elif brightness_change == 0:
        in_file.close()
        return 0





def set_bright(original_brightness):
    if (original_brightness == 0):
        new_brightness = 1
        os.system("echo 60 | sudo tee /sys/class/backlight/rpi_backlight/brightness")
    else:
        if (original_brightness == 1):
            new_brightness = 2
            os.system("echo 170 | sudo tee /sys/class/backlight/rpi_backlight/brightness")
        else:
            new_brightness = 0
            os.system("echo 250 | sudo tee /sys/class/backlight/rpi_backlight/brightness")

    return(new_brightness)