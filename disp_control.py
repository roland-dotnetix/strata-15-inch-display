import numpy as np
import cv2

import schedule
import time
import datetime
import threading
import subprocess
import os

from safeye_configuration import (safeye_configuration,
                                  configuration_create_default_file,
                                  configuration_read,
                                  configuration_update)
from disp_sockets import SafEyeSocket

from safeye_server import (safeye_server,
                           server_user_active,
                           server_update_cameras,
                           server_selected_camera,
                           server_update_display_values,
                           server_is_camera_selected,
                           server_update_status_values,
                           server_update_software_version,
                           server_new_configuration,
                           server_get_configuration,
                           server_update_configuration)
from disp_sounds import sound_condition, beep

from touch import det_touch, set_bright

SOFTWARE_VERSION = "Disp_HDMI_RTG_V1.0"
print("Starting SafEye Nano control version:", SOFTWARE_VERSION)

if 'XDG_RUNTIME_DIR' not in os.environ:
    os.environ['XDG_RUNTIME_DIR'] = '/run/user/1002'

# Connection fixed values
SERVER_IP = '0.0.0.0'
SERVER_PORT = 80
#DISPLAY_STREAM_IP = '172.17.1.2'
#DISPLAY_STREAM_IP_2 = '172.17.1.3'
#DISPLAY_STREAM_PORT = 5000
#DISPLAY_AUDIO_IP = DISPLAY_STREAM_IP
#DISPLAY_AUDIO_IP_2 = DISPLAY_STREAM_IP_2
#DISPLAY_AUDIO_PORT = 5001

# Input lists
ports_to_open = [5000, 5001, 5002, 5003]
ports_opened = [0, 0, 0, 0]
ports_last_updates = [datetime.datetime.now()] * 4
returns = [0, 0, 0, 0]
camera_disconnected_counter = [0, 0, 0, 0]
camera_threads = []

# Display fixed values
display_width = int(1920)#int(800)
display_height = int(1080)#int(480)
display_frame_rate = 15
display_jpeg_quality = 90

# Camera fixed values
camera_connection_timeout = 5   # Seconds
server_camera_update_interval = 0.2   # Seconds NOTE: VALUE MUST BE <1
#max_cameras = 412
counts_before_camera_disconnect = 1
camera_width = int(640)
camera_height = int(360)
startup = True

font = cv2.FONT_HERSHEY_SIMPLEX
#aspect_ratio = int(camera_width*10/camera_height)

#Initialising global variables
cameras_to_display_previous = safeye_configuration["cameras_to_display"]
#temperature_file_location = ""
#temperature_file = None
#temperature = 0
global brightness
global touching
global touch_time

logo = cv2.imread("splash_logo.png")
#Initialise gstream writer
video_writer_string = "appsrc ! videoconvert ! waylandsink fullscreen=true sync=false"#fbdevsink"#waylandsink fullscreen=true" #'appsrc ! videoconvert ! videorate ! video/x-raw, format=(string)BGRx, width=800, height=480 ! waylandsink fullscreen=true sync=false' # autovideosink

gstreamer_writer = cv2.VideoWriter(video_writer_string, cv2.CAP_GSTREAMER, display_frame_rate,(display_width,display_height), True)
#gstreamer_writer.write(logo)


gstreamer_video_stream_command = ("gst-launch-1.0 udpsrc port=5000 ! application/x-rtp,media=video,encoding-name=JPEG,payload=96 ! rtpjpegdepay ! jpegdec ! videoconvert ! appsink")

#("gst-launch-1.0 udpsrc port=5000 ! application/x-rtp, media=video, "
                                  #"encoding-name=JPEG, payload=96 ! rtpjpegdepay ! jpegdec ! videoconvert ! "
                                  #"videoscale ! video/x-raw, width=800, height=480, "
                                  #"pixel-aspect-ratio=1/1 ! autovideosink") # autovideosink


def create_text_frame(text, r, g, b):
    #print("tried to make text frame")
    text_frame = np.zeros((camera_height, camera_width, 3), np.uint8)
    text_size = cv2.getTextSize(text, font, 1.7, 3)[0]
    text_x = int((text_frame .shape[1] - text_size[0]) / 2)
    text_y = int((text_frame .shape[0] + text_size[1]) / 2)
    cv2.putText(text_frame, str(text), (text_x, text_y), font, 1.7, (b, g, r), 3)
    return text_frame


frames = [create_text_frame("CAMERA CONNECTING", 255, 255, 255)] * 4
#frames[0] = logo


class GstreamerStream(threading.Thread):
    def __init__(self, gstreamer_input):
        print("Starting thread: Gstreamer with command:")
        print(gstreamer_input)
        threading.Thread.__init__(self)
        self.gstreamer_input = gstreamer_input

    def run(self):

        while True:
            try:
                subprocess.call(self.gstreamer_input, shell=True)
                time.sleep(2)
                print("No gstreamer pipe found or gstreamer pipe broke")

            except:
                time.sleep(2)



class CameraCaptureThread(threading.Thread):
    def __init__(self, index):
        threading.Thread.__init__(self)
        print("Starting camera capture thread at index:", index)
        self.index = index
        self.returns = False
        self.frame = create_text_frame("CAMERA CONNECTING", 255, 255, 255)
        self.frame_height = 0
        self.frame_width = 0
        self.frame_channels = 0
        self.capture = None
        self.video_capture_string = ""
        self.alive = True

    def gstreamer_connect(self):
        global ports_opened, ports_to_open, ports_last_updates
        global returns, frames

        print("-" * 50)
        returns[self.index] = False
        if startup:
            #frames[self.index] = logo
            print("first frame")
        else:
            #frames[self.index] = create_text_frame("NO CONNECTION", 255, 255, 0)
            print("second frame")
        self.video_capture_string = 'udpsrc port=' + str(ports_to_open[self.index]) + ' ! application/x-rtp, encoding-name=JPEG,payload=26 ! rtpjpegdepay ! jpegdec ! videoconvert ! appsink sync=false'
        print("Gstreamer capture: Attempting to open VideoCapture:", self.index, "on port:", ports_to_open[self.index])
        print(self.video_capture_string)
        print("~" * 50)

        # Attempt to open the port

        self.capture = cv2.VideoCapture(self.video_capture_string, cv2.CAP_GSTREAMER)


        if not self.capture.isOpened():
            print('Gstreamer capture: ERROR: VideoCapture', self.index, 'not opened')
            ports_opened[self.index] = False
            returns[self.index] = False
            frames[self.index] = create_text_frame("CONNECTION ERROR", 255, 255, 0)


        else:
            print('Gstreamer capture: VideoCapture', self.index, 'opened')
            ports_opened[self.index] = True
            returns[self.index] = False
            frames[self.index] = create_text_frame("NO STREAM", 255, 0, 0)

        print("^" * 50)

    def kill(self):
        print("Killing thread", self.index)
        self.alive = False

    def run(self):

        global ports_opened
        self.gstreamer_connect()

        while self.alive:
            #print(str(datetime.datetime.now()) + " start thread loop for " + str(self.index))
            if not ports_opened[self.index]:
                time.sleep(3)

                #frames[self.index] = create_text_frame("No Connection", 255, 255, 0)
                self.gstreamer_connect()
                print("Attempting to connect")

            else:

                self.returns, self.frame = self.capture.read()
                #print(str(datetime.datetime.now()) + " after thread " + str(self.index))

                if not self.returns:
                 #   print('Gstreamer capture: Empty frame ', self.index)
                    returns[self.index] = False
                    frames[self.index] = create_text_frame("NO STREAM", 255, 0, 0)

                else:
                    self.frame_height, self.frame_width, self.frame_channels = self.frame.shape
                    if self.frame_height == camera_height and self.frame_width == camera_width:
                        returns[self.index] = self.returns
                        frames[self.index] = self.frame
                    else:
                        returns[self.index] = False
                        frames[self.index] = create_text_frame("STREAM ERROR", 255, 0, 0)
                    ports_last_updates[self.index] = datetime.datetime.now()

            time.sleep(0.020)

        try:
            self.capture.release()
        #    print("Capture released")
        except:
            print("No capture to release")


# Start the camera threads
def spawn_camera_threads():
    global camera_width, camera_height
    print("Main: Spawn camera threads: Spawning camera threads")
    for j in range(len(camera_threads)):
        print("Killing camera thread", j)
        camera_threads[j].kill()

    camera_threads.clear()

    for j in range(safeye_configuration["cameras_to_display"]):
        camera_threads.append(CameraCaptureThread(j))
        camera_threads[j].daemon = True
        camera_threads[j].start()
    print("Main: Spawn camera threads: Threads spawned")


class AudioThread(threading.Thread):
    #audio_ip = DISPLAY_AUDIO_IP
    #audio_port = DISPLAY_AUDIO_PORT
    beep_flag = False
    warning = 0

    def __init__(self):
        #global DISPLAY_AUDIO_IP, DISPLAY_AUDIO_PORT
        threading.Thread.__init__(self)
        print("~~~~~~~~~~~~~~~~~~ start AUDIO thread ************")

        self.alive = True

    def set_beep(self):
        AudioThread.beep_flag = True


    def set_warning(self, warning):
        AudioThread.warning = warning

    def kill(self):
        #print("Killing audio thread")
        self.alive = False

    def run(self):
        #print(self.alive)
        while self.alive:

            if AudioThread.beep_flag:
                print("flag found")
                beep(AudioThread.warning)
                AudioThread.beep_flag = False
            time.sleep(0.01)




#Touch Thread
def touch_thread():
    global touching, touch_time, brightness

    brightness = 2

    while 1:
        #t = time.clock()
        time.sleep(0.05)
        touching = det_touch()
        if (touching == 1):
            time.sleep(0.025)
            touch_time = datetime.datetime.now().timestamp() * 1000
            #time.sleep(0.1)
        elif (touching == 2):
            time.sleep(0.025)
            tt = datetime.datetime.now().timestamp() * 1000
            if ((touching == 2) and ((tt - touch_time) <= 5000)):
                touch_time = ((datetime.datetime.now().timestamp() * 1000))
                #print("changing brightness")
                brightness = set_bright(brightness)
                time.sleep(0.075)
            else:
                touch_time = ((datetime.datetime.now().timestamp() * 1000))

        #print(str(time.clock() - t))





def connection_status_checks():
    global gstreamer_writer
    if not gstreamer_writer:
        gstreamer_writer = cv2.VideoWriter(video_writer_string, cv2.CAP_GSTREAMER, display_frame_rate,(display_width, display_height), True)
    print("Main loop: Connected cameras: ", safeye_sockets.safeye_count)

    if not safeye_sockets.connected:
        safeye_sockets.start_socket_server()


def cam_config_status_check():
    global cameras_to_display_previous
    print("Main loop: 5 second event")
    if safeye_configuration["cameras_to_display"] != cameras_to_display_previous:
        spawn_camera_threads()
        cameras_to_display_previous = safeye_configuration["cameras_to_display"]


def update_cameras():
    if not server_is_camera_selected():
        if len(cameras_to_render) == safeye_configuration["cameras_to_display"]:
            server_frame = frame
        else:
            server_frame = make_frame(list(range(safeye_configuration["cameras_to_display"])))
        server_update_cameras(server_frame)
    elif (server_selected_camera() >= 0) & (server_selected_camera() < 4):
        server_update_cameras(frames[server_selected_camera()].copy())


class GstreamerStream(threading.Thread):
    def __init__(self, gstreamer_input):
        print("Starting thread: Gstreamer with command:")
        print(gstreamer_input)
        threading.Thread.__init__(self)
        self.gstreamer_input = gstreamer_input

    def run(self):

        while True:
            try:
                subprocess.call(self.gstreamer_input, shell=True)
                time.sleep(2)
                print("No gstreamer pipe found or gstreamer pipe broke")

            except:
                print("ERROR GSTREAMER pipe broke")
                time.sleep(1)
                continue



def det_direction_line(frame,detection_list):
    for i in detection_list:
        blank_top = np.zeros((10, 320, 3), np.uint8)
        blank_sides = np.zeros((180, 10, 3), np.uint8)
        #print("detection list: " + str(i))
        if i == 0: #front camera

            if (safeye_sockets.warnings[i] == 2) or (safeye_sockets.warnings[i] == 5) or (safeye_sockets.warnings[i] == 6):
                #front_block = cv2.rectangle(blank_top, (0, 0), (320, 10), (0, 0, 255), -1)
                frame = cv2.rectangle(frame, (200, 0), (600, 15), (0, 0, 255), -1)
            if (safeye_sockets.warnings[i] == 3):
                #front_block = cv2.rectangle(blank_top, (0, 0), (320, 10), (255, 0, 0), -1)
                frame = cv2.rectangle(frame, (200, 0), (600, 15), (255, 0, 0), -1)
            if (safeye_sockets.warnings[i] == 4):
                #front_block = cv2.rectangle(blank_top, (0, 0), (320, 10), (0, 255, 255), -1)
                frame = cv2.rectangle(frame, (200, 0), (600, 15), (0, 255, 255), -1)

            #front_block = cv2.addWeighted(frame[0:10,160:480],0.5,front_block,0.5,0)
            #frame[0:10,160:480] = front_block

                #frame = cv2.rectangle(frame, (160, 5), (480, 15), (0, 255, 255), -1)
            #Creates a rectangle on (x,y) to (x1,y1) in (B,G,R) color with border thickness -1 (-1 fills block)
        elif i == 1: #rear camera
            if (safeye_sockets.warnings[i] == 2) or (safeye_sockets.warnings[i] == 5) or (safeye_sockets.warnings[i] == 6):
                #rear_block = cv2.rectangle(blank_top, (0, 0), (320, 10), (0, 0, 255), -1)
                frame = cv2.rectangle(frame, (200, 465), (600, 480), (0, 0, 255), -1)
            if (safeye_sockets.warnings[i] == 3):
                #rear_block = cv2.rectangle(blank_top, (0, 0), (320, 10), (255, 0, 0), -1)
                frame = cv2.rectangle(frame, (200, 465), (600, 480), (255, 0, 0), -1)
            if (safeye_sockets.warnings[i] == 4):
                #rear_block = cv2.rectangle(blank_top, (0, 0), (320, 10), (0, 255, 255), -1)
                frame = cv2.rectangle(frame, (200, 465), (600, 480), (0, 255, 255), -1)

            #rear_block = cv2.addWeighted(frame[350:360,160:480],0.5,rear_block,0.5,0)
            #frame[350:360,160:480] = rear_block

                #frame = cv2.rectangle(frame, (160, 345), (480, 355), (0, 255, 255), -1)
            # Creates a rectangle on (x,y) to (x1,y1) in (B,G,R) color with border thickness -1 (-1 fills block)
        elif i == 2: #left camera
            if (safeye_sockets.warnings[i] == 2) or (safeye_sockets.warnings[i] == 5) or (safeye_sockets.warnings[i] == 6):
                #left_block = cv2.rectangle(blank_sides, (0, 0), (10, 180), (0, 0, 255), -1)
                frame = cv2.rectangle(frame, (0, 120), (15, 360), (0, 0, 255), -1)
            if (safeye_sockets.warnings[i] == 3):
                #left_block = cv2.rectangle(blank_sides, (0, 0), (10, 180), (255, 0, 0), -1)
                frame = cv2.rectangle(frame, (0, 120), (15, 360), (255, 0, 0), -1)
            if (safeye_sockets.warnings[i] == 4):
                #left_block = cv2.rectangle(blank_sides, (0, 0), (10, 180), (0, 255, 255), -1)
                frame = cv2.rectangle(frame, (0, 120), (15, 360), (0, 255, 255), -1)

            #left_block = cv2.addWeighted(frame[90:270, 0:10], 0.5, left_block, 0.5, 0)
            #frame[90:270, 0:10] = left_block

                #frame = cv2.rectangle(frame, (5, 90), (20, 270), (0, 255, 255), -1)
            # Creates a rectangle on (x,y) to (x1,y1) in (B,G,R) color with border thickness -1 (-1 fills block)
        elif i == 3: #right camera
            if (safeye_sockets.warnings[i] == 2) or (safeye_sockets.warnings[i] == 5) or (safeye_sockets.warnings[i] == 6):
                #right_block = cv2.rectangle(blank_sides, (0, 0), (10, 180), (0, 0, 255), -1)
                frame = cv2.rectangle(frame, (785, 120), (800, 360), (0, 0, 255), -1)
            if (safeye_sockets.warnings[i] == 3):
                #right_block = cv2.rectangle(blank_sides, (0, 0), (10, 180), (255, 0, 0), -1)
                frame = cv2.rectangle(frame, (785, 120), (800, 360), (255, 0, 0), -1)
            if (safeye_sockets.warnings[i] == 4):
                #right_block = cv2.rectangle(blank_sides, (0, 0), (10, 180), (0, 255, 255), -1)
                frame = cv2.rectangle(frame, (785, 120), (800, 360), (0, 255, 255), -1)

            #right_block = cv2.addWeighted(frame[90:270, 630:640], 0.5, right_block, 0.5, 0)
            #frame[90:270, 630:640] = right_block
            # Creates a rectangle on (x,y) to (x1,y1) in (B,G,R) color with border thickness -1 (-1 fills block)

    return frame



def make_frame(camera_list):
    if safeye_configuration["multi_cam"] == 0:
        out_frame = cv2.resize(frames[0], (display_width, display_height))
    else:
        # 1x Camera connected ----------------------------------------------------------------------------------------------
        if len(camera_list) == 1:
            if frames[camera_list[0]].size != [800, 480]:
                frame = cv2.resize(frames[camera_list[0]], (display_width, display_height))
            else:
                frame = frames[camera_list[0]]
            out_frame = frame

            # print("Tried to display 1 frames")
        # 2x Camera connected ----------------------------------------------------------------------------------------------
        elif len(camera_list) == 2:
            out_frame = cv2.hconcat([frames[camera_list[0]], frames[camera_list[1]]])
            out_frame = cv2.copyMakeBorder(out_frame, int(camera_height / 2), int(camera_height / 2), 0, 0,
                                       cv2.BORDER_CONSTANT, (0, 0, 0))
            out_frame = cv2.resize(out_frame, (display_width, display_height))
            # print("Tried to display 2 frames")

        # 3x Camera connected ----------------------------------------------------------------------------------------------
        elif len(camera_list) == 3:
            frame_top = cv2.hconcat([frames[camera_list[0]], frames[camera_list[1]]])
            frame_bottom = cv2.copyMakeBorder(frames[camera_list[2]], 0, 0, int(camera_width / 2),
                                              int(camera_width / 2),
                                              cv2.BORDER_CONSTANT, (0, 0, 0))
            out_frame = cv2.vconcat([frame_top, frame_bottom])
            out_frame = cv2.resize(out_frame, (display_width, display_height))

        # 4x Camera connected ----------------------------------------------------------------------------------------------
        elif len(camera_list) == 4:
            out_frame = cv2.vconcat([cv2.hconcat([frames[camera_list[0]], frames[camera_list[1]]]),
                                 cv2.hconcat([frames[camera_list[2]], frames[camera_list[3]]])])
            out_frame = cv2.resize(out_frame, (display_width, display_height))

        # No cameras connected ---------------------------------------------------------------------------------------------
        else:
            out_frame = create_text_frame("NO CAMERAS", 255, 255, 255)
            out_frame = cv2.resize(out_frame, (display_width, display_height))
    return out_frame


if __name__ == "__main__":


    time.sleep(1)
    #os.system("sudo service lightdm stop")
    #threadGstreamerVideo = GstreamerStream(gstreamer_video_stream_command)
    #threadGstreamerVideo.daemon = True
    #threadGstreamerVideo.start()

    print("starting main before touch")

    global touch_time
    global touching
    global brightness
    touching = 0
    brightness = 2
    touch_time = ((datetime.datetime.now().timestamp() * 1000) - 20000) #sets initial touch time value to > 5 seconds

    # Reload configuration
    if not configuration_read():
        configuration_create_default_file()
    else:
        print("successfully read configuration", safeye_configuration["warn_relays"])

    print("Main startup: Starting sockets")
    # Connect sockets
    safeye_sockets = SafEyeSocket()
    safeye_sockets.start_socket_server()
    print("Main startup: Sockets started")

    print("Main startup: Spawning camera threads")
    spawn_camera_threads()
    print("Main startup: Camera threads spawned")

    print("Main startup: Starting server")
    if safeye_configuration["multi_cam"] == 1:
        os.system("sudo ifconfig eth0:1 172.17.1.1 netmask 255.255.255.0")
        os.system("sudo ifconfig eth0:1 up")
    else:
        os.system("sudo ifconfig eth0:1 172.17.1.2 netmask 255.255.255.0")
        os.system("sudo ifconfig eth0:1 up")
        gstreamer_audio_stream_command = (
            f"gst-launch-1.0 -e udpsrc port=5001 ! application/x-rtp,clock-rate=48000,payload=97 ! "
            f"rtpL16depay ! audioconvert ! audioresample ! "
            f'alsasink device="hdmi:CARD=vc4hdmi1,DEV=0"'
        )
        threadGstreamerAudio = GstreamerStream(gstreamer_audio_stream_command)
        threadGstreamerAudio.daemon = True
        threadGstreamerAudio.start()

    # Start the server
    server_update_cameras(create_text_frame("LOADING CAMERA FEED", 255, 255, 255))
    server_update_display_values(display_width, display_height, camera_width, camera_height)
    SafeyeServerThread = threading.Thread(target=safeye_server, args=(SERVER_IP, SERVER_PORT))
    SafeyeServerThread.daemon = True
    SafeyeServerThread.start()
    server_update_software_version(SOFTWARE_VERSION)
    server_update_configuration(safeye_configuration["zone_frequency_warn"],
                                safeye_configuration["zone_frequency_slow"],
                                safeye_configuration["zone_frequency_stop"],
                                safeye_configuration["zone_frequency_void"],
                                safeye_configuration["cameras_to_display"],
                                safeye_configuration["alert_volume"],
                                safeye_configuration["multi_cam"])

    print("Main startup: Server started")

    AudioThread().daemon = True
    AudioThread().start()
    sounds = AudioThread()

    # Initialise local variables
    loop_start = 0
    loop_average = 0
    warning_current = 0
    warning_previous = 0
    object_current = ""
    distance_current = 0
    time_last_beep = datetime.datetime.now()
    disconnect_flag = [0, 0, 0, 0]
    cameras_to_render = []

    # Define schedule timers
    schedule.every(5).seconds.do(connection_status_checks)
    schedule.every(5).seconds.do(cam_config_status_check)
    schedule.every(server_camera_update_interval).seconds.do(update_cameras)

    # Alert user that startup has completed
    sounds.set_warning(4)
    sounds.set_beep()

    #Start touch input threading
    T_thread = threading.Thread(target=touch_thread)
    T_thread.start()

    while True:
        if safeye_configuration["multi_cam"] == 0:
            if not threadGstreamerAudio.is_alive():
                threadGstreamerAudio.run()
            # loop_start = datetime.datetime.now()
        cameras_to_render = []
        det_line_list = []

        # Check if cameras have disconnected ---------------------------------------------------------------------------
        for i in range(safeye_configuration["cameras_to_display"]):
            if (datetime.datetime.now() - ports_last_updates[i]).seconds > camera_connection_timeout:
                camera_disconnected_counter[i] += 1
                if (camera_disconnected_counter[i] == counts_before_camera_disconnect) & (disconnect_flag[i] == 0):
                    disconnect_flag[i] = 1
                    startup = False
                    if ports_opened[i]:
                        frames[i] = create_text_frame("CONNECTION LOST", 255, 0, 0)
                        print("Main loop: Gstreamer connection lost on camera thread:", i, "on port:", ports_to_open[i])
                    else:
                        frames[i] = create_text_frame("CAMERA CONNECTING", 255, 255, 255)
                        print("Main loop: Gstreamer unable to open camera:", i, "on port:", ports_to_open[i])
            else:
                disconnect_flag[i] = 0
                camera_disconnected_counter[i] = 0

        # Handle socket communications ---------------------------------------------------------------------------------
        if safeye_sockets.connected:

            safeye_sockets.handle_socket_communications()
            warning_current = 0
            for i in range(safeye_configuration["cameras_to_display"]):
                if safeye_sockets.warnings[i] >= warning_current:
                    warning_current = safeye_sockets.warnings[i]
                    object_current = safeye_sockets.objects[i]
                    distance_current = safeye_sockets.distances[i]
                    if warning_current >= 2:
                        if disconnect_flag[i] == 0:
                            #cameras_to_render.append(i)
                            det_line_list.append(i)
                            if sound_condition(time_last_beep, warning_current, warning_previous):
                                sounds.set_warning(warning_current)
                                sounds.set_beep()
                                #print("tried to beep")
                                #if warning_current != warning_previous:
                                   #num_beeps = 3
                                #else:
                                    #num_beeps = 1

                                #beep(warning_current)
                                time_last_beep = datetime.datetime.now()
                                warning_previous = warning_current

        else:
            # Create a warning for no connected cameras
            warning_current = safeye_sockets.warning_invalid

        # Normal rendering if there are no warnings
        if not cameras_to_render:
            cameras_to_render = list(range(safeye_configuration["cameras_to_display"]))
            #print(str(cameras_to_render))

        frame = make_frame(cameras_to_render)
        frame = det_direction_line(frame, det_line_list)

        #t0 = time.clock()
        tt = datetime.datetime.now().timestamp() * 1000
        #check if touch event within 5 seconds
        if (((tt - touch_time)) <= 5000):
            #Create new frame containing brightness Image.
            brighImg = cv2.imread("/home/dotnetix/dotnetix/brightness.jpg", cv2.IMREAD_COLOR)
            rows,cols,channels = brighImg.shape
            overlay = cv2.addWeighted(frame[190:190+rows,700:700+cols],0.5,brighImg,0.5,0)
            #new_frame = frame
            #new_frame[190:190+rows,700:700+cols] = overlay
            frame[190:190+rows,700:700+cols] = overlay
            #brightframetime = time.clock() - t0
            #print("time to make bright frame = " + str(brightframetime))



        # Write frame to gstreamer -------------------------------------------------------------------------------------
        gstreamer_writer.write(frame)
        #print("tried to show frame")
        if server_user_active():
            if server_new_configuration():
                print("Main loop: new configuration!")
                (safeye_configuration["zone_frequency_warn"],
                safeye_configuration["zone_frequency_slow"],
                safeye_configuration["zone_frequency_stop"],
                safeye_configuration["zone_frequency_void"],
                safeye_configuration["cameras_to_display"],
                safeye_configuration["alert_volume"],
                 safeye_configuration["multi_cam"]) = server_get_configuration()

                server_update_configuration(safeye_configuration["zone_frequency_warn"],
                                         safeye_configuration["zone_frequency_slow"],
                                         safeye_configuration["zone_frequency_stop"],
                                         safeye_configuration["zone_frequency_void"],
                                         safeye_configuration["cameras_to_display"],
                                         safeye_configuration["alert_volume"],
                                         safeye_configuration["multi_cam"])

                configuration_update()

        server_update_status_values(safeye_sockets.connected, safeye_sockets.safeye_count)

        schedule.run_pending()
        time.sleep(0.020)
        #cv2.imshow('receive', frame)
