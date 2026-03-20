import struct
import time
import sys

infile_path = "/dev/input/event0"
FORMAT = 'llHHI'
EVENT_SIZE = struct.calcsize(FORMAT)

#open file in binary mode
in_file = open(infile_path, "rb")

event = in_file.read(EVENT_SIZE)
time = 0
time2 = 0
while event:
    (tv_sec, tv_usec, type, code, value) = struct.unpack(FORMAT, event)

    if type != 0 or code != 0 or value != 0:
        #print("Event type %u, code %u, value %u at %d.%d" % \
        #    (type, code, value, tv_sec, tv_usec))
        if code == 53:
            x = value
        if code == 54:
            y = value
        if code == 330:
            if value == 1:
                time = tv_sec + tv_usec/1000000
                print("Screen touch at x: "+ str(x) + " and y: " + str(y))
            else:
                time2 = tv_sec + tv_usec/1000000
                print("touch released after: " + str(time2-time))
    else:
        # Events with code, type and value == 0 are "separator" events
        print("===========================================")

    event = in_file.read(EVENT_SIZE)

in_file.close()
