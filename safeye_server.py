from flask import Flask, Response, redirect, url_for, request, session, abort, render_template, make_response, g, jsonify
from flask_login import LoginManager, UserMixin, login_required, fresh_login_required, login_user, logout_user, current_user, user_logged_in
from werkzeug.utils import secure_filename
import xml.etree.ElementTree as ET
import threading
import numpy as np
import cv2
import datetime
import os
import zipfile
import time

# For HTML grids, see:
# https://www.w3schools.com/css/tryit.asp?filename=trycss_grid_layout_named

lock = threading.Lock()

server_user_active_bool = False

app = Flask(__name__)

#ALLOWED_EXTENSIONS = {"py", "zip"}
#ALLOWED_FILES = {"safeye_nano_control.py", "safeye_sockets.py", "safeye_server.py"}

ALLOWED_EXTENSIONS = {"zip"}
ALLOWED_FILES = {"safeye_disp_DSI.zip"}

app.config.update(
    SECRET_KEY='safeye@123',
    UPLOAD_FOLDER=''
)

login_manager = LoginManager()

user_file_name = "users.xml"

# Create default user
users = []

# flask-login
login_manager.init_app(app)
login_manager.login_view = "login"

server_display_width = 640
server_display_height = 360

server_camera_width = int(server_display_width / 2)
server_camera_height = int(server_display_height / 2)

server_display_enlarge_ratio = 1

camera_display_frame = np.zeros((server_display_height, server_display_width, 3), np.uint8)

camera_selected = False
point_selected = False
selected_camera = 0

calibration_point = [0, 0, 0, 0]
new_calibration_point = False
calibration_point_returned = False

server_temperature = 0
server_socket_server = False
server_socket_connections = 0
server_48V = 0
server_5V = 0
server_3_3V = 0
server_GPS_connected = False
server_GPS_time = ""
server_GPS_alt = 0
server_GPS_speed = 0
server_GPS_lat = ""
server_GPS_long = ""
server_decoded_relays = [0, 0, 0, 0]

server_software_version = 0

server_new_configuration_bool = False
server_multi_cam = 0
server_zone_frequency_warn = 0
server_zone_frequency_slow = 0
server_zone_frequency_stop = 0
server_zone_frequency_void = 0
server_cameras_to_display = 0
server_alert_volume = 1
server_warn_relays_int = 0
server_slow_relays_int = 0
server_stop_relays_int = 0

server_message_zone_update = ""
server_message_cameras_update = ""
server_message_alert_volume_update = ""
server_message_multi_cam_update = ""

relays_dict = {'warn': {1: 0, 2: 0, 3: 0, 4: 0}, 'slow': {1: 0, 2: 0, 3: 0, 4: 0}, 'stop': {1: 0, 2: 0, 3: 0, 4: 0}}
active_relays_count = {'warn': 0, 'slow': 0, 'stop': 0}

server_relay_message = ["", "", ""]

PASSWORD_ZIP = b'safeye@123'


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def server_update_display_values(display_width, display_height, camera_width, camera_height):
    global server_display_width
    global server_display_height

    global server_camera_width
    global server_camera_height

    server_display_width = display_width
    server_display_height = display_height

    server_camera_width = camera_width
    server_camera_height = camera_height


def server_new_configuration():
    return server_new_configuration_bool


def server_get_configuration():

    global server_new_configuration_bool

    global server_multi_cam
    global server_zone_frequency_warn
    global server_zone_frequency_slow
    global server_zone_frequency_stop
    global server_zone_frequency_void
    global server_cameras_to_display
    global server_alert_volume

    server_new_configuration_bool = False

    print("Server: Returning Configuration: Warn: ", server_zone_frequency_warn,
          "Slow: ", server_zone_frequency_slow,
          "Stop: ", server_zone_frequency_stop,
          "Void: ", server_zone_frequency_void,
          "Cameras: ", server_cameras_to_display,
          "Volume: ", server_alert_volume,
          "Multi_cam: ", server_multi_cam)

    return (server_zone_frequency_warn,
            server_zone_frequency_slow,
            server_zone_frequency_stop,
            server_zone_frequency_void,
            server_cameras_to_display,
            server_alert_volume,
            server_multi_cam
            )


def server_update_configuration(zone_frequency_warn_input, zone_frequency_slow_input, zone_frequency_stop_input,
                                zone_frequency_void_input, connected_cameras_input, alert_volume_input, multi_cam):

    global server_zone_frequency_warn, server_zone_frequency_slow, server_zone_frequency_stop, \
        server_zone_frequency_void, server_cameras_to_display, server_alert_volume, server_multi_cam

    server_zone_frequency_warn = zone_frequency_warn_input
    server_zone_frequency_slow = zone_frequency_slow_input
    server_zone_frequency_stop = zone_frequency_stop_input
    server_zone_frequency_void = zone_frequency_void_input
    server_cameras_to_display = connected_cameras_input
    server_alert_volume = alert_volume_input
    server_multi_cam = multi_cam


def server_update_software_version(software_version_input):
    global server_software_version

    server_software_version = software_version_input


def server_update_status_values(socket_server_input,
                                socket_server_connections_input):

    global server_temperature
    global server_socket_server
    global server_socket_connections
    global server_48V, server_5V, server_3_3V
    global server_GPS_connected
    global server_GPS_time
    global server_GPS_alt
    global server_GPS_speed
    global server_GPS_lat
    global server_GPS_long
    global server_decoded_relays

    server_socket_server = socket_server_input
    server_socket_connections = socket_server_connections_input


# User model
class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id
        self.name = "safeye"
        self.password = "safeye@123"

    def update_user_details(self, user_name, user_password):
        self.name = user_name
        self.password = user_password

    def user_id(self):
        return self.id

    def user_name(self):
        return self.name

    def user_password(self):
        return self.password

    def __repr__(self):
        return "%d/%s/%s" % (self.id, self.name, self.password)


# Create default users file
def create_default_users_file():
    print("Server: Creating new default users file...")
    try:
        os.remove(user_file_name)
        print("Server: Old user file deleted")
    except:
        print("Server: No user file present, creating new one")
    user_tree = ET.ElementTree()
    user_root = ET.Element("users")

    user_el_tag = ET.SubElement(user_root, "user")

    user_el_id = ET.SubElement(user_el_tag, "user_id")
    user_el_id.text = "0"

    user_el_name = ET.SubElement(user_el_tag, "user_name")
    user_el_name.text = "admin"

    user_el_password = ET.SubElement(user_el_tag, "user_password")
    user_el_password.text = "admin"

    user_tree._setroot(user_root)
    user_tree.write(user_file_name)


# Read users from file:
def read_users_file():
    print("Server: Reading users file...")
    global users

    users.clear()

    try:
        tree = ET.parse(user_file_name)
        xml_users = tree.getroot()
        for xml_user in xml_users:

            user_id = 0
            user_name = ""
            user_password = ""

            user_id_error = True
            user_name_error = True
            user_password_error = True

            for detail in xml_user:
                if detail.tag == "user_id":
                    user_id = int(detail.text)
                    user_id_error = False

                elif detail.tag == "user_name":
                    user_name = detail.text
                    user_name_error = False

                elif detail.tag == "user_password":
                    user_password = detail.text
                    user_password_error = False

            if not user_id_error and not user_name_error and not user_password_error:
                print("Server: User loaded: ID:", user_id, "Name:", user_name, "Password:", user_password)

                users.append(User(user_id))
                users[-1].update_user_details(user_name, user_password)

            else:
                print("Server ERROR: Error reading user file: Tags not found")

    except:
        print("Server ERROR: Error reading user file: File IO error")


def update_users_file(user_id_input, user_name_input, user_password_input):
    print("Server: Updating user with ID:", user_id_input, "New name:", user_name_input, "New password:", user_password_input)
    try:
        tree = ET.parse(user_file_name)
        xml_users = tree.getroot()
        for xml_user in xml_users:
            for detail in xml_user:
                if detail.tag == "user_id":
                    if user_id_input == int(detail.text):
                        try:

                            xml_user.find("user_name").text = user_name_input
                            xml_user.find("user_password").text = user_password_input

                        except:
                            print("Server ERROR: Updating user: Tags not found")
                            return False

                        try:
                            tree.write(user_file_name)
                        except:
                            print("Server ERROR: Updating user: File write IO error")
                            return False

                        read_users_file()
                        print("Server: User updated")

                        return True
        print("Server ERROR: Updating user: User not found")

    except:
        print("Server ERROR: Updating user: File open or read IO error")
        return False

    return False


read_users_file()

if len(users) == 0:
    print("Server: no users loaded from user file")
    create_default_users_file()
    read_users_file()


@app.before_request
def before_request():
    print("Server: Before request called...")
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=10)
    session.modified = True
    g.user = current_user


# some protected url
@app.route("/")
@fresh_login_required
def index():
    print("Server: '/' requested")
    return render_template("index.html", nav_bar=True)


def server_update_cameras(display_input):

    global camera_display_frame

    if server_user_active():

        lock.acquire()
        camera_display_frame = cv2.resize(display_input, (server_display_width * server_display_enlarge_ratio, server_display_height * server_display_enlarge_ratio))
        lock.release()


def generate():

    global camera_display_frame

    while True:

        with lock:
            (flag, encodedImage) = cv2.imencode(".jpg", camera_display_frame)

        yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n'


camera_open_message = ""


@app.route("/cameras")
@fresh_login_required
def cameras():
    print("Server: '/cameras' requested")
    global camera_selected
    global selected_camera
    global calibration_point
    global server_user_active_bool

    global camera_open_message

    server_user_active_bool = True

    print("Server: Reset camera selection")
    print("Server: Reset calibration point")
    camera_selected = False
    selected_camera = 0
    calibration_point = [0, 0, 0, 0]

    return render_template("cameras.html",
                           message_open_camera=camera_open_message, nav_bar=True, title='Cameras')


@app.route("/camera")
@fresh_login_required
def camera():
    print("Server: '/camera' requested")
    global camera_selected
    global selected_camera
    global calibration_point
    global server_user_active_bool
    global camera_open_message

    server_user_active_bool = True

    return render_template("cameras.html", nav_bar=True, title='Cameras')


@app.route('/camera_calibration', methods=['GET', 'POST'])
@fresh_login_required
def camera_calibration():
    print("Server: '/camera_calibration' requested")

    global camera_selected
    global selected_camera
    global calibration_point
    global new_calibration_point

    point_quadrant = 0
    calibration_point = [0, 0, 0, 0]

    x = request.form['text1']
    y = request.form['text2']

    print("Server: Camera display clicked. X:", int(x), "Y:", int(y))

    if (int(x) / server_display_enlarge_ratio) <= (server_display_width / 2) and (int(y) / server_display_enlarge_ratio) <= (server_display_height / 2):
        point_quadrant = 0

    elif (int(x) / server_display_enlarge_ratio) >= (server_display_width / 2) and (int(y) / server_display_enlarge_ratio) <= (server_display_height / 2):
        point_quadrant = 1

    elif (int(x) / server_display_enlarge_ratio) <= (server_display_width / 2) and (int(y) / server_display_enlarge_ratio) >= (server_display_height / 2):
        point_quadrant = 2

    elif (int(x) / server_display_enlarge_ratio) >= (server_display_width / 2) and (int(y) / server_display_enlarge_ratio) >= (server_display_height / 2):
        point_quadrant = 3

    print("Server: Camera click quadrant:", point_quadrant)

    if not camera_selected:

        camera_selected = True
        new_calibration_point = False
        if server_cameras_to_display == 1:
            selected_camera = 0
        elif server_cameras_to_display == 2:
            if point_quadrant == 0 or point_quadrant == 2:
                selected_camera = 0
            elif point_quadrant == 1 or point_quadrant == 3:
                selected_camera = 1
        elif server_cameras_to_display == 3:
            if point_quadrant == 0:
                selected_camera = 0
            elif point_quadrant == 1:
                selected_camera = 1
            elif point_quadrant == 2 or point_quadrant == 3:
                selected_camera = 2
        else:
            selected_camera = int(point_quadrant)
        print("Server: Selected camera", selected_camera)
        #return redirect(url_for('cameras'))

    else:

        y_value_to_send = 0

        if point_quadrant == 0 or point_quadrant == 1:
            y_value_to_send = 0

        elif point_quadrant == 2 or point_quadrant == 3:
            y_value_to_send = server_camera_height

        reduce_ratio = ((server_display_width * server_display_enlarge_ratio) / server_camera_width)

        print("Server: New calibration point: Selected camera:", selected_camera, "Point:", point_quadrant, "X:", x, "Y:", y_value_to_send)

        calibration_point = [selected_camera, point_quadrant, int(int(x) / reduce_ratio), y_value_to_send]

        new_calibration_point = True

    return_string = x.upper() + y.upper()

    result_response = {
        "output": return_string
    }
    result_response = {str(key): value for key, value in result_response.items()}
    #return redirect(url_for('cameras'))
    return jsonify(result=result_response)


@app.route("/camera_open", methods=['GET', 'POST'])
@fresh_login_required
def camera_open():
    print("Server: '/camera_open' requested")

    global camera_selected
    global selected_camera
    global camera_open_message

    if request.method == 'POST':
        if camera_selected:

            ip = "http://172.17.1.2" + str(selected_camera) + ":4000"

            """if selected_camera == 0:
                ip = "//172.17.1.20"
            elif selected_camera == 1:
                ip = "//172.17.1.21"
            elif selected_camera == 2:
                ip = "//172.17.1.22"
            elif selected_camera == 3:
                ip = "//172.17.1.23"""""

            return redirect(ip, 302)

        else:
            camera_open_message = "Select a camera first"

    return redirect(url_for('cameras'))


@app.route("/camera_display")
@fresh_login_required
def camera_display():
    # return the response generated along with the specific media
    # type (mime type)
    print("Server: '/camera_display' requested")
    if server_user_active():
        return Response(generate(),
                        mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/status")
@fresh_login_required
def status():
    print("Server: '/status' requested")

    global server_user_active_bool

    server_user_active_bool = True
    return render_template("status.html",
                           value_temperature=server_temperature,
                           value_socket_server=server_socket_server,
                           value_socket_cons=server_socket_connections,
                           value_server_5v=server_5V,
                           value_server_3_3v=server_3_3V,
                           value_GPS_connected=server_GPS_connected,
                           value_GPS_time=server_GPS_time,
                           value_GPS_alt=server_GPS_alt,
                           value_GPS_speed=server_GPS_speed,
                           value_GPS_lat=server_GPS_lat,
                           value_GPS_long=server_GPS_long,
                           value_relay_0=server_decoded_relays[0],
                           value_relay_1=server_decoded_relays[1],
                           value_relay_2=server_decoded_relays[2],
                           value_relay_3=server_decoded_relays[3],
                           nav_bar=True, title='Status')


@app.route('/update_status_values', methods=['GET'])
def update_status_values():
    print("Server: '/update_status_values' requested")

    return jsonify(json_crtl_temp=server_temperature,
                   json_socket_serv=server_socket_server,
                   json_socket_cons=server_socket_connections,
                   json_3_3v=server_3_3V,
                   json_5v=server_5V,
                   json_GPS_con=server_GPS_connected,
                   json_GPS_time=server_GPS_time,
                   json_GPS_alt=server_GPS_alt,
                   json_GPS_speed=server_GPS_speed,
                   json_GPS_lat=server_GPS_lat,
                   json_GPS_long=server_GPS_long,
                   json_relay_0=server_decoded_relays[0],
                   json_relay_1=server_decoded_relays[1],
                   json_relay_2=server_decoded_relays[2],
                   json_relay_3=server_decoded_relays[3])


admin_update_user_message = " Awaiting input..."
admin_upload_software_message = " Select a file..."


@app.route("/admin")
@fresh_login_required
def admin():
    print("Server: '/admin' requested")

    global server_software_version
    global admin_update_user_message
    global admin_upload_software_message

    return render_template("admin.html",
                           update_user_message=admin_update_user_message,
                           nav_bar=True, title="Admin")


@app.route("/admin_update_user", methods=["GET", "POST"])
@fresh_login_required
def admin_update_user():
    print("Server: '/admin_update_user' requested")

    global admin_update_user_message

    if request.method == 'POST':
        print("Server: User update requested")
        old_username = request.form['old_username']
        new_username = request.form['new_username']

        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_new_password = request.form['confirm_new_password']

        print("Server: User update requested: Old username:", old_username, "New username:", new_username, "Old password:", old_password, "New password:", new_password)

        for user in users:
            if old_username == user.user_name() and old_password == user.user_password():
                print("Server: User update requested: Old username and password correct")

                if len(new_username) < 4:
                    print("Server: User update requested: Username too short")
                    admin_update_user_message = "New username too short, use at least 4 characters..."
                    return redirect(url_for('admin'))

                if len(new_password) < 4:
                    print("Server: User update requested: Password too short")
                    admin_update_user_message = "New password too short, use at least 4 characters..."
                    return redirect(url_for('admin'))

                if new_password != confirm_new_password:
                    print("Server: User update requested: Password confirmation mismatch")
                    admin_update_user_message = "Password confirmation did not match..."
                    return redirect(url_for('admin'))

                if update_users_file(user.id, new_username, new_password):
                    print("Server: User update requested: User updated")
                    admin_update_user_message = "User updated!"
                    return redirect(url_for('admin'))

                print("Server: User update requested: Unspecified error")
                admin_update_user_message = "Unspecified error"
                return redirect(url_for('admin'))

        print("Server: User update requested: Incorrect old username or password")
        admin_update_user_message = "Incorrect old username or old password"
        return redirect(url_for('admin'))

    admin_update_user_message = "Awaiting input..."
    return redirect(url_for('admin'))


@app.route("/update")
@fresh_login_required
def update():
    print("Server: '/update' requested")

    global server_software_version
    global admin_update_user_message
    global admin_upload_software_message

    return render_template("update.html",
                           software_version_message=server_software_version,
                           upload_software_message=admin_upload_software_message, nav_bar=True, title="Update")


@app.route("/update_upload_software", methods=["GET", "POST"])
@fresh_login_required
def update_upload_software():
    print("Server: '/admin_upload_software' requested")

    global admin_upload_software_message

    if request.method == 'POST':
        # check if the post request has the file part

        if 'file' not in request.files:
            print("Server: Upload file: No file returned")
            admin_upload_software_message = "No file selected"
            return redirect(url_for('update'))

        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            print("Server: Upload file: Browser supplied empty file")
            admin_upload_software_message = "No file selected"
            return redirect(url_for('update'))

        if not allowed_file(file.filename):
            print("Server: Upload file: Incorrect file type")
            admin_upload_software_message = "Incorrect file type"
            return redirect(url_for('update'))

        if file.filename not in ALLOWED_FILES:
            print("Server: Upload file: File not supported")
            admin_upload_software_message = "File not supported"
            return redirect(url_for('update'))

        if file:
            print("Server: Uploading file:", file.filename)
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            try:
                with zipfile.ZipFile(file.filename) as zip_file:
                    zip_file.extractall(pwd=PASSWORD_ZIP)
            except:
                print("Server ERROR: Upload file: Unzip error")
                admin_upload_software_message = "Unspecified error, check zip file"
                return redirect(url_for('update',
                                        filename=admin))

            admin_upload_software_message = "Software uploaded! Restart to take affect..."
            return redirect(url_for('update',
                                    filename=admin))

    admin_upload_software_message = " Select a file..."
    return redirect(url_for('update'))


@app.route("/update_reboot", methods=["GET", "POST"])
@fresh_login_required
def update_reboot():
    print("Server: '/update_reboot' requested")
    print("Server: Calling reboot...")
    if request.method == 'POST':
        if server_user_active():
            if request.form['reboot'] == 'Reboot':
                os.system('sudo shutdown -r now')

    return redirect(url_for('logout'))


@app.route("/configuration")
@fresh_login_required
def configuration():
    print("Server: '/configuration' requested")

    global server_user_active_bool
    global server_new_configuration_bool

    global server_zone_frequency_warn, server_zone_frequency_slow, server_zone_frequency_stop, server_zone_frequency_void
    global server_cameras_to_display, server_multi_cam, server_message_multi_cam_update

    global server_message_zone_update
    global server_message_cameras_update
    global server_relay_message
    server_user_active_bool = True
    #server_new_configuration_bool = False
    server_warn_relays = [relays_dict['warn'][1], relays_dict['warn'][2], relays_dict['warn'][3], relays_dict['warn'][4]]
    server_slow_relays = [relays_dict['slow'][1], relays_dict['slow'][2], relays_dict['slow'][3], relays_dict['slow'][4]]
    server_stop_relays = [relays_dict['stop'][1], relays_dict['stop'][2], relays_dict['stop'][3], relays_dict['stop'][4]]

    return render_template("configuration.html",
                           value_warn_zone=server_zone_frequency_warn,
                           value_slow_zone=server_zone_frequency_slow,
                           value_stop_zone=server_zone_frequency_stop,
                           value_void_zone=server_zone_frequency_void,
                           message_zone_update=server_message_zone_update,
                           value_cameras_to_display=server_cameras_to_display,
                           message_cameras_to_display_update=server_message_cameras_update,
                           value_alert_volume=server_alert_volume,
                           message_alert_volume_update=server_message_alert_volume_update,
                           warn_zone_relay_msg=server_relay_message[0],
                           slow_zone_relay_msg=server_relay_message[1],
                           stop_zone_relay_msg=server_relay_message[2],
                           warn_relays_value=server_warn_relays,
                           slow_relays_value=server_slow_relays,
                           stop_relays_value=server_stop_relays,
                           value_multi_cam=server_multi_cam,
                           message_multi_cam_update=server_message_multi_cam_update,
                           title='Configuration', nav_bar=True)


@app.route("/configuration_update", methods=["GET", "POST"])
@fresh_login_required
def configuration_update():
    print("Server: '/configuration_update' requested")

    global server_new_configuration_bool
    global server_user_active_bool

    global server_message_zone_update, server_message_cameras_update, server_message_alert_volume_update
    global server_zone_frequency_warn, server_zone_frequency_slow, server_zone_frequency_stop, server_zone_frequency_void
    global server_cameras_to_display, server_multi_cam, server_message_multi_cam_update
    global server_alert_volume
    global server_relay_message

    server_user_active_bool = True

    server_message_zone_update = ""

    if request.method == 'POST':
        print("Server: Update zone frequencies requested")
        label_warn_zone = request.form['warn_zone_frequency_update']
        label_slow_zone = request.form['slow_zone_frequency_update']
        label_stop_zone = request.form['stop_zone_frequency_update']
        label_void_zone = request.form['void_zone_frequency_update']
        label_cameras_to_display = request.form['cameras_to_display']
        label_alert_volume = request.form['alert_volume_update']
        label_multi_cam = request.form['multi_cam_update']

        print("Server: Update Configuration: Warn:", label_warn_zone,
              "Slow:", label_slow_zone,
              "Stop:", label_stop_zone,
              "void:", label_void_zone,
              "Cameras:", label_cameras_to_display)

        if label_warn_zone:
            if 0.2 <= float(label_warn_zone) <= 10:
                server_zone_frequency_warn = float(label_warn_zone)
                server_message_zone_update += "Warn zone frequency updated. "
            else:
                server_message_zone_update += "Warn zone frequency invalid. "
        else:
            server_message_zone_update += ""

        if label_slow_zone:
            if 0.2 <= float(label_slow_zone) <= 10:
                server_zone_frequency_slow = float(label_slow_zone)
                server_message_zone_update += "Slow zone frequency updated. "
            else:
                server_message_zone_update += " Slow zone invalid. "
        else:
            server_message_zone_update += ""

        if label_stop_zone:
            if 0.2 <= float(label_stop_zone) <= 10:
                server_zone_frequency_stop = float(label_stop_zone)
                server_message_zone_update += "Stop zone frequency updated."
            else:
                server_message_zone_update += " Stop zone invalid."
        else:
            server_message_zone_update += ""

        if label_void_zone:
            if 0.2 <= float(label_void_zone) <= 10:
                server_zone_frequency_void = float(label_void_zone)
                server_message_zone_update += "Void zone frequency updated."
            else:
                server_message_zone_update += " Void zone invalid."
        else:
            server_message_zone_update += ""

        if int(label_cameras_to_display) != 0:
            server_cameras_to_display = int(label_cameras_to_display)
            server_message_cameras_update = "Cameras updated"
        else:
            server_message_cameras_update = ""

        if label_alert_volume:
            if 1 <= float(label_alert_volume) <= 100:
                server_alert_volume = float(label_alert_volume)
                server_message_alert_volume_update = "Volume updated"
            else:
                server_message_alert_volume_update = "Volume invalid"
        else:
            server_message_alert_volume_update = ""
        if label_multi_cam:
            if label_multi_cam != server_multi_cam:
                server_multi_cam = label_multi_cam
                server_message_multi_cam_update = "Display type updated"

        # check for clear then loop through dict updating values
        for i in ['warn', 'slow', 'stop', 'void']:
            request_string_clear = "relay_" + str(i) + "_clear"
            active_relays_count[i] = 0
            for j in range(1, 5):
                request_string = "relay_" + str(i) + "_" + str(j)
                try:
                    if request.form[request_string_clear] != None:
                        relays_dict[i][j] = 0
                except:
                    try:
                        if request.form[request_string] != None:
                            relays_dict[i][j] = 1
                    except:
                        if False:
                            print("This message should not be able to be printed")

        encode_relays()
        server_relay_message = make_relay_messages()

    server_new_configuration_bool = True
    return redirect(url_for('configuration'))


# somewhere to login
@app.route("/login", methods=["GET", "POST"])
def login(username="", password=""):
    print("Server: '/login' requested")

    global server_user_active_bool

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        print("Server: Login details provided...")

        for user in users:
            if username == user.user_name() and password == user.user_password():
                login_user(user, remember=False)
                server_user_active_bool = True
                print("Server: Login successful")
                return redirect("/")

        print("Server: Login unsuccessful: Incorrect username or password")
        return render_template("login.html", message="Incorrect user or password, please try again")

    else:
        return render_template("login.html", message="Please enter user name and password", username=username, password=password, nav_bar=False)


# somewhere to logout
@app.route("/logout")
@login_required
def logout():
    print("Server: '/logout' requested")

    global server_user_active_bool

    logout_user()
    server_user_active_bool = False
    return redirect("/login")


# handle login failed
@app.errorhandler(401)
def page_not_found(e):
    print("Server: Error 401 handled")
    return Response('<p>Error</p>')


# callback to reload the user object
@login_manager.user_loader
def load_user(userid):
    print("Server: load user executed")
    return User(userid)


def server_new_calibration_point():
    global calibration_point
    global new_calibration_point

    if new_calibration_point:
        return True

    return False


def server_camera_calibration_point():

    global calibration_point
    global new_calibration_point

    new_calibration_point = False
    print("Server: Calibration point returned")
    return calibration_point


def server_is_camera_selected():

    global camera_selected
    return camera_selected


def server_selected_camera():
    global selected_camera
    return selected_camera


def server_user_active():

    global server_user_active_bool

    return server_user_active_bool
    #return server_user_logged_in
    #return users[0].is_active


def encode_relays():
    global server_warn_relays_int, server_slow_relays_int, server_stop_relays_int, active_relays_count
    server_warn_relays_int = 0
    server_slow_relays_int = 0
    server_stop_relays_int = 0
    active_relays_count['warn'] = 0
    active_relays_count['slow'] = 0
    active_relays_count['stop'] = 0
    for i in range(1, 5):
        server_warn_relays_int += relays_dict['warn'][i] * pow(2, i - 1)
        active_relays_count['warn'] += relays_dict['warn'][i]
        server_slow_relays_int += relays_dict['slow'][i] * pow(2, i - 1)
        active_relays_count['slow'] += relays_dict['slow'][i]
        server_stop_relays_int += relays_dict['stop'][i] * pow(2, i - 1)
        active_relays_count['stop'] += relays_dict['stop'][i]


def make_relay_messages():
    global active_relays_count
    new_relay_message = []
    for i in ['warn', 'slow', 'stop', 'void']:
        if active_relays_count[i] == 0:
            new_relay_message.append("No relays enabled")
        elif active_relays_count[i] == 1:
            for j in range(1, 5):
                if relays_dict[i][j]:
                    new_relay_message.append("Relay " + str(j) + " is enabled")
        elif active_relays_count[i] < 4:
            relay_message_builder = "Relays "
            relays_message_counter = 0
            for j in range(1, 5):
                if relays_dict[i][j]:
                    relays_message_counter += 1
                    if relays_message_counter == 1:
                        relay_message_builder += str(j)
                    elif relays_message_counter == active_relays_count[i]:
                        relay_message_builder += " and " + str(j) + " are enabled"
                    elif relays_message_counter == 2:
                        relay_message_builder += ", " + str(j)
            new_relay_message.append(relay_message_builder)
        else:
            new_relay_message.append("All relays enabled")
    return new_relay_message


def safeye_server(host, port):

    while True:
        try:
            print("Server: Starting server...")
            app.run(host=host, port=port, debug=True, threaded=True, use_reloader=False)
        except:
            print("Server ERROR: Unable to start server, port may be in use, try again in 5 seconds...")

        time.sleep(30)

"""SafeyeServerThread = threading.Thread(target=safeye_server)
SafeyeServerThread.daemon = True
SafeyeServerThread.start()"""





