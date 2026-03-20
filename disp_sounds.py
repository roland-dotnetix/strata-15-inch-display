import datetime
import disp_sockets
from safeye_configuration import (safeye_configuration)
import subprocess

sf = disp_sockets.SafEyeSocket()
s_dict = {sf.COL_INHIBIT_ZONE: {'vol': '1', 'buf': '2', 'freq': '1800'},
          sf.COL_STOP_ADVISORY_ZONE: {'vol': '0.8', 'buf': '4', 'freq': '500'},
          sf.COL_SLOWDOWN_INTERVENTION_ZONE: {'vol': '0.8', 'buf': '3', 'freq': '600'},
          sf.COL_STOP_INTERVENTION_ZONE: {'vol': '1', 'buf': '2', 'freq': '1800'},
          sf.COL_VOID_ZONE: {'vol': '1', 'buf': '2', 'freq': '2500'}}


def sound_condition(time_last_beep, curr_warning, prev_warning):
    global sf
    if curr_warning > 1:
        if curr_warning > prev_warning:
            return True
        else:
            time_gap = (datetime.datetime.now()-time_last_beep).seconds + (datetime.datetime.now()-time_last_beep).microseconds/1000000.0
            if (curr_warning == sf.COL_INHIBIT_ZONE) & (time_gap >= safeye_configuration["zone_frequency_stop"]):
                return True
            elif (curr_warning == sf.COL_STOP_ADVISORY_ZONE) & (time_gap >= safeye_configuration["zone_frequency_warn"]):
                return True
            elif (curr_warning == sf.COL_SLOWDOWN_INTERVENTION_ZONE) & (time_gap >= safeye_configuration["zone_frequency_slow"]):
                return True
            elif (curr_warning == sf.COL_STOP_INTERVENTION_ZONE) & (time_gap >= safeye_configuration["zone_frequency_stop"]):
                return True
            elif (curr_warning == sf.COL_VOID_ZONE) & (time_gap >= safeye_configuration["zone_frequency_void"]):
                return True
    return False



def beep(curr_warning):
    command = ("gst-launch-1.0 audiotestsrc volume=" + str(float(s_dict[curr_warning]['vol'])*safeye_configuration["alert_volume"]/100.0) +
               " num-buffers=" + s_dict[curr_warning]['buf'] + " freq=" + s_dict[curr_warning]['freq'] +
               " wave=2 ! alsasink")
    subprocess.call(command, shell=True)