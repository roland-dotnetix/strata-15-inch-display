# !/usr/bin/env python3
import socket
import selectors
import types
import time


class SafEyeSocket:
    def __init__(self, host='', port=3001, max_cameras=4):
        self.host = host
        self.port = port

        self.max_cameras = max_cameras

        self.connected = False

        self.connected_ips = []

        self.safeye_count = 0

        self.receive_data = []
        self.send_messages = []
        self.send_message = ""
        self.sel = selectors.DefaultSelector()

        self.warning_invalid = -1
        self.COL_OBJECT_MOVING_AWAY = 0
        self.COL_OBJECT_OUT_OF_RANGE = 1
        self.COL_INHIBIT_ZONE = 2
        self.COL_STOP_ADVISORY_ZONE = 3
        self.COL_SLOWDOWN_INTERVENTION_ZONE = 4
        self.COL_STOP_INTERVENTION_ZONE = 5
        self.COL_VOID_ZONE = 6

        self.warnings = [self.warning_invalid] * self.max_cameras
        self.objects = [""] * self.max_cameras
        self.distances = [0.0] * self.max_cameras

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print("accepted connection from", addr)
        self.connected_ips.append(addr)
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data=data)
        self.safeye_count = len(self.connected_ips)

    def service_connection(self, key, mask):
        self.receive_data = None
        sock = key.fileobj
        data = key.data
        data.outb = None
        if self.send_message:
            data.outb = self.send_message.encode()

        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                #data.outb += recv_data
                safeye_string = repr(recv_data)
                self.receive_data = safeye_string.split(":")

                try:
                    #print("Data:", self.receive_data)
                    #Example:
                    #Data: ["b'1", '0', '1', 'person', '5', '0.609200', '1', '671', '546', '511.202789', "'"]
                    if isinstance(self.receive_data, list):
                        #print("Data is list")
                        if len(self.receive_data) > 4:
                            #print("Data longer than 4")
                            if str(self.receive_data[0]) == "b'1":
                                #print("ID is safeye_object")
                                if self.receive_data[2] == "1":
                                    #print("Warning active, warning level:", self.receive_data[4])
                                    self.warnings[int(self.receive_data[1])] = int(self.receive_data[4])
                                    self.objects[int(self.receive_data[1])] = self.receive_data[3]
                                    self.distances[int(self.receive_data[1])] = float(self.receive_data[5])
                                else:
                                    #print("No warning active")
                                    self.warnings[int(self.receive_data[1])] = 0

                except:
                    print("Safeye sockets: Unable to parse message")

                #print("Warnings:", self.warnings)

            else:
                print("Socket server: ERROR: Unable to read from", data.addr, "closing connection")
                self.sel.unregister(sock)
                self.connected_ips.remove(data.addr)
                self.safeye_count = len(self.connected_ips)
                try:
                    self.warnings[int(data.addr[0][-1:])] = 0
                except:
                    self.warnings = [self.warning_invalid] * self.max_cameras
                #sock.close()

        #print("Preparing to write")
        if mask & selectors.EVENT_WRITE:
            #print("Event write")
            if data.outb:
                #print("Data outb")
                #safeye_string = repr(data.outb)
                #new_data = safeye_string.split(":")
                #print("echoing = ", repr(data.outb), "to", data.addr)
                #msg = b"safeye:" + b"10" + b":" + b"1" + b"\n"
                #msg = "1".encode()
                try:
                    sent = sock.send(data.outb)  # Should be ready to write
                    data.outb = data.outb[sent:]
                    #msg = msg[sent:]
                    #msg = ""
                except:
                    print("Socket server: ERROR: Unable to write to", data.addr, "closing connection")
                    self.sel.unregister(sock)
                    self.connected_ips.remove(data.addr)
                    self.safeye_count = len(self.connected_ips)
                    try:
                        self.warnings[int(data.addr[0][-1:])] = 0
                    except:
                        self.warnings = [self.warning_invalid] * self.max_cameras

        """data.outb = self.send_messages[0].encode()"""

        """if mask & selectors.EVENT_WRITE:
            if data.outb:
                # safeye_string = repr(data.outb)
                # new_data = safeye_string.split(":")
                # print("echoing = ", repr(data.outb), "to", data.addr)
                msg = b"safeye:" + b"10" + b":" + b"1" + b"\n"
                try:
                    sent = sock.send(msg)  # Should be ready to write
                    data.outb = data.outb[sent:]
                    # msg = msg[sent:]
                    # msg = ""
                except:
                    self.sel.close()"""



        #if len(self.send_messages):
            #self.send_messages.append("")

        """for message in self.send_messages:
            print("sending:", message)
            data.outb = message
            send = message.encode()
            if mask & selectors.EVENT_WRITE:
                if data.outb:
                    try:
                        sent = sock.send(send)  # Should be ready to write
                        data.outb = data.outb[sent:]
                    except:
                        self.sel.close()"""

    def send_calibration_message(self, camera_id, point, x_value, y_value):
        self.send_messages.append("safeye_calibration:" + str(camera_id) + ":" + str(point) + ":" + str(x_value) + ":" + str(y_value))

    def send_gps_message(self, gps_speed, gps_lat, gps_long):
        self.send_messages.append("safeye_gps:" + str(gps_speed) + ":" + str(gps_lat) + ":" + str(gps_long))

    def start_socket_server(self):
        print("Starting SafEye socket server...")

        try:
            lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            lsock.bind((self.host, self.port))
            lsock.listen()
            print("listening on", (self.host, self.port))
            lsock.setblocking(False)
            self.sel.register(lsock, selectors.EVENT_READ, data=None)
            self.connected = True

        except:
            self.warnings = [self.warning_invalid] * self.max_cameras
            self.connected = False
            print("Unable to open socket")

    def handle_socket_communications(self):
        if self.connected:
            try:

                if len(self.send_messages) > 0:
                    self.send_message = self.send_messages.pop(0)

                else:
                    self.send_message = "FF"

                #print("ips:", self.connected_ips)
                #print("warnings", self.warnings)

                #print("getting events")
                events = self.sel.select(timeout=0.001)
                #print("got events")

                for key, mask in events:
                    #print("key:", key, "mask", mask)
                    if key.data is None:
                        #print("key data is none???")
                        self.accept_wrapper(key.fileobj)
                    else:
                        #print("servicing connection")
                        self.service_connection(key, mask)

                return True

            except:
                """print("Socket server: ERROR: Select error, closing socket server")
                self.sel.close()
                self.connected = False
                self.warnings = [0] * max_cameras
                return False"""

                print("Socket server: ERROR: Select error, waiting 1 second before retrying...")
                self.warnings = [self.warning_invalid] * self.max_cameras
                time.sleep(0.01)
