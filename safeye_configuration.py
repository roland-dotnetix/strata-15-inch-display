import xml.etree.ElementTree as ET
import os
from collections import OrderedDict

configuration_file_location = "configuration.xml"

"""safeye_configuration = OrderedDict([("zone_frequency_warn", 3),
                                    ("zone_frequency_slow", 2),
                                    ("zone_frequency_stop", 1)])"""

safeye_configuration = {"configuration_version": "1.00",
                        "multi_cam": 0,
                        "zone_frequency_warn": 3.0,
                        "zone_frequency_slow": 2.0,
                        "zone_frequency_stop": 1.0,
                        "zone_frequency_void": 1.0,
                        "cameras_to_display": 2,
                        "alert_volume": 0.0,
                        "warn_relays": 0,
                        "slow_relays": 3,
                        "stop_relays": 6}


# Create default configuration file
def configuration_create_default_file():
    print("Configuration: Creating new default configuration file...")
    try:
        os.remove(configuration_file_location)
        print("Configuration: Old configuration file deleted")
    except:
        print("Configuration: No configuration file present, creating new one")

    configuration_tree = ET.ElementTree()
    configuration_root = ET.Element("configuration")

    configuration_version = ET.SubElement(configuration_root, "configuration_version")
    configuration_version.text = str(safeye_configuration["configuration_version"])

    configuration_zone_frequency_warn = ET.SubElement(configuration_root, "Multi-camera_display")
    configuration_zone_frequency_warn.text = str(safeye_configuration["multi_cam"])

    configuration_zone_frequency_warn = ET.SubElement(configuration_root, "zone_frequency_warn")
    configuration_zone_frequency_warn.text = str(safeye_configuration["zone_frequency_warn"])

    configuration_zone_frequency_slow = ET.SubElement(configuration_root, "zone_frequency_slow")
    configuration_zone_frequency_slow.text = str(safeye_configuration["zone_frequency_slow"])

    configuration_zone_frequency_stop = ET.SubElement(configuration_root, "zone_frequency_stop")
    configuration_zone_frequency_stop.text = str(safeye_configuration["zone_frequency_stop"])

    configuration_zone_frequency_void = ET.SubElement(configuration_root, "zone_frequency_void")
    configuration_zone_frequency_void.text = str(safeye_configuration["zone_frequency_void"])

    configuration_cameras_to_display = ET.SubElement(configuration_root, "cameras_to_display")
    configuration_cameras_to_display.text = str(safeye_configuration["cameras_to_display"])

    configuration_alert_volume = ET.SubElement(configuration_root, "alert_volume")
    configuration_alert_volume.text = str(safeye_configuration["alert_volume"])

    configuration_alert_volume = ET.SubElement(configuration_root, "warn_relays")
    configuration_alert_volume.text = str(safeye_configuration["warn_relays"])

    configuration_alert_volume = ET.SubElement(configuration_root, "slow_relays")
    configuration_alert_volume.text = str(safeye_configuration["slow_relays"])

    configuration_alert_volume = ET.SubElement(configuration_root, "stop_relays")
    configuration_alert_volume.text = str(safeye_configuration["stop_relays"])

    configuration_tree._setroot(configuration_root)
    configuration_tree.write(configuration_file_location)


# Read users from file:
def configuration_read():
    print("Configuration: Reading configuration file...")

    try:
        configuration_tree = ET.parse(configuration_file_location)
        configuration_root = configuration_tree.getroot()

        for configuration in configuration_root:

            configuration_version_found = False
            zone_frequency_warn_found = False
            zone_frequency_slow_found = False
            zone_frequency_stop_found = False
            cameras_to_display_found = False

            if configuration.tag == "configuration_version":
                safeye_configuration["configuration_version"] = configuration.tag

            elif configuration.tag == "Multi-camera_display":
                safeye_configuration["multi_cam"] = float(configuration.text)
                zone_frequency_warn_found = True

            elif configuration.tag == "zone_frequency_warn":
                safeye_configuration["zone_frequency_warn"] = float(configuration.text)
                zone_frequency_warn_found = True

            elif configuration.tag == "zone_frequency_slow":
                safeye_configuration["zone_frequency_slow"] = float(configuration.text)
                zone_frequency_slow_found = True

            elif configuration.tag == "zone_frequency_stop":
                safeye_configuration["zone_frequency_stop"] = float(configuration.text)
                zone_frequency_stop_found = True

            elif configuration.tag == "zone_frequency_void":
                safeye_configuration["zone_frequency_void"] = float(configuration.text)
                zone_frequency_void_found = True

            elif configuration.tag == "cameras_to_display":
                safeye_configuration["cameras_to_display"] = int(configuration.text)
                cameras_to_display_found = True

            elif configuration.tag == "alert_volume":
                safeye_configuration["alert_volume"] = float(configuration.text)
                print("made it to alert vol")

            elif configuration.tag == "warn_relays":
                safeye_configuration["warn_relays"] = int(configuration.text)

            elif configuration.tag == "slow_relays":
                safeye_configuration["slow_relays"] = int(configuration.text)

            elif configuration.tag == "stop_relays":
                safeye_configuration["stop_relays"] = int(configuration.text)



            else:
                print("Configuration ERROR: Error reading configuration file: Unknown tag")

    except:
        print("Server ERROR: Error reading user file: File IO error")
        return False

    print("Configuration: Finished reading configuration: Version:",
          safeye_configuration["configuration_version"],
          "Multi_cam:", safeye_configuration["multi_cam"],
          "Zone frequency warn:", safeye_configuration["zone_frequency_warn"],
          "Zone frequency slow:", safeye_configuration["zone_frequency_slow"],
          "Zone frequency stop:", safeye_configuration["zone_frequency_stop"],
          "Zone frequency void:", safeye_configuration["zone_frequency_void"],
          "Cameras to display:", safeye_configuration["cameras_to_display"],
          "alert_volume: ", safeye_configuration["alert_volume"],
          "Warn relays:", safeye_configuration["warn_relays"],
          "Slow relays:", safeye_configuration["slow_relays"],
          "Stop relays:", safeye_configuration["stop_relays"])
    return True


def configuration_update():
    print("Configuration: Updating configuration with zone_frequency_warn: ",
          safeye_configuration["zone_frequency_warn"],
          "Multi_cam:", safeye_configuration["multi_cam"],
          "zone_frequency_slow: ", safeye_configuration["zone_frequency_slow"],
          "zone_frequency_stop: ", safeye_configuration["zone_frequency_stop"],
          "Zone frequency void:", safeye_configuration["zone_frequency_void"],
          "cameras_to_display: ", safeye_configuration["cameras_to_display"],
          "alert_volume: ", safeye_configuration["alert_volume"],
          "Warn relays:", safeye_configuration["warn_relays"],
          "Slow relays:", safeye_configuration["slow_relays"],
          "Stop relays:", safeye_configuration["stop_relays"])
    try:
        configuration_tree = ET.parse(configuration_file_location)
        configuration_root = configuration_tree.getroot()
        configuration_root.find("Multi-camera_display").text = str(safeye_configuration["multi_cam"])
        configuration_root.find("zone_frequency_warn").text = str(safeye_configuration["zone_frequency_warn"])
        configuration_root.find("zone_frequency_slow").text = str(safeye_configuration["zone_frequency_slow"])
        configuration_root.find("zone_frequency_stop").text = str(safeye_configuration["zone_frequency_stop"])
        configuration_root.find("zone_frequency_void").text = str(safeye_configuration["zone_frequency_void"])
        configuration_root.find("cameras_to_display").text = str(safeye_configuration["cameras_to_display"])
        configuration_root.find("alert_volume").text = str(safeye_configuration["alert_volume"])
        configuration_root.find("warn_relays").text = str(safeye_configuration["warn_relays"])
        configuration_root.find("slow_relays").text = str(safeye_configuration["slow_relays"])
        configuration_root.find("stop_relays").text = str(safeye_configuration["stop_relays"])

        configuration_tree._setroot(configuration_root)
        configuration_tree.write(configuration_file_location)

    except:
        print("Server ERROR: Updating user: File open or read IO error")
        return False

    return False