from pymavlink import mavutil
import sys
import serial, serial.serialutil, serial.tools.list_ports
import time
from threading import Thread

mavlink_results = {
    0: "Accepted            ",
    1: "Temporarily Rejected",
    2: "Denied              ",
    3: "Unsupported         ",
    4: "Failed              ",
    5: "In Progress         ",
    6: "Cancelled           ",
    7: "long-only           ",
    8: "int-only            ",
    9: "Unsupported Frame   ",
    10: "Permission Denied  ",
}

def connect_mavlink(device, baud) -> bool:
    global connection
    connection = mavutil.mavlink_connection(device=device, baud=baud)
    try:
        msg = connection.wait_heartbeat(timeout=5)
        if not msg: raise mavutil.mavlink.MAVError()
        print(msg)
        print(f"Heartbeat received from system {connection.target_system}, component {connection.target_component}")
        return True
    except mavutil.mavlink.MAVError:
        print("No heartbeat received.")
        return False

def keep_heartbeating():
    while not end:
        connection.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
        time.sleep(0.9)
        print("Heartbeat sent.")

def setup():
    global end, log_file
    end = False
    log_file = f"FC_logs/FC_log_{time.strftime("%Y%m%d_%H%M%S")}.csv"
    heartbeat_thread = Thread(target=keep_heartbeating)
    with open("config.txt", 'r') as file:
        data = [x.strip() for x in file.readlines()]
    serial_com = data[0].split(',')[0].strip()
    serial_baud = data[0].split(',')[1].strip()
    mavlink_com = data[1].split(',')[0].strip()
    mavlink_baud = data[1].split(',')[1].strip()
    start_log_read = data[2]
    motor = data[3]
    esc = data[4]
    batt = data[5]
    prop = data[6]
    print(f"Prop    : {prop}\nMotor   : {motor}\nESC     : {esc}\nBattery : {batt}")
    s = input("Testing same configuration? ")
    if s in 'yY':
        pass
    else:
        n = -1
        while n:
            if n>0:
                print(f"Prop    : {prop}\nMotor   : {motor}\nESC     : {esc}\nBattery : {batt}")
            print("1> Prop\n2> Motor\n3> ESC\n4> Battery")
            n = int(input("Update: "))
            if n==1:
                prop = input("Enter prop: ")
            elif n==2:
                with open("components.txt", 'r') as file2:
                    items = [x.strip() for x in file2.readlines()]
                items[:] = items[items.index("Motor")+1:]
                items[:] = [x for x in items if x]
                for i, opn in enumerate(items):
                    print(f"{i+1}> {opn}")
                motor = items[int(input("Enter motor: "))-1]
            elif n==3:
                with open("components.txt", 'r') as file2:
                    items = file2.readlines()
                items[:] = items[items.index("ESC")+1 : items.index('', items.index("ESC")+1)]
                for i, opn in enumerate(items):
                    print(f"{i+1}> {opn}")
                esc = items[int(input("Enter ESC: "))-1]
            elif n==4:
                with open("components.txt", 'r') as file2:
                    items = [x.strip() for x in file2.readlines()]
                items[:] = items[items.index("Battery")+1 : items.index('', items.index("Battery")+1)]
                for i, opn in enumerate(items):
                    print(f"{i+1}> {opn}")
                batt = items[int(input("Enter battery: "))-1]
        print(f"{motor}\n{esc}\n{batt}\n{prop}")
    print("Configuration confirmed.")
    with open(log_file, 'a') as file:
        print(f"{time.strftime("%Y-%m-%d %H:%M:%S")},{prop},{motor},{esc},{batt}", file=file)
    print(f"MAVLink COM: {mavlink_com}, {mavlink_baud}")
    s = input("Use last configuration? y/n: ")
    if s in 'Yy':
        pass
    else:
        comports = sorted([str(x) for x in serial.tools.list_ports.comports()])
        for (i, port) in enumerate(comports):
            print(f"{i+1}. {port}")
        mavlink_com = comports[int(input("Choose MAVLink COM Port: "))-1]
        mavlink_baud = int(input("Enter MAVLink baud: "))
    b = connect_mavlink(mavlink_com, mavlink_baud)
    if b:
        print("COM Ports set up correctly.")
        with open("config.txt", 'w') as file:
            print(f"{serial_com},{serial_baud}", file=file)
            print(f"{mavlink_com},{mavlink_baud}", file=file)
            print(start_log_read, file=file)
            print(f"{motor}\n{esc}\n{batt}\n{prop}", file=file)
    else:
        print("Data input not initialised correctly.")
        print(f"MAV ({mavlink_com}): {b}")
        sys.exit(0)
    heartbeat_thread.start()

    print("Setting up MAVLink data...")
    # 65, 74, 147, 226, 291, 11030
    interval = 200000
    connection.mav.command_long_send(
        connection.target_system, connection.target_component, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, 147, interval, 0, 0, 0, 0, 0, 0)
    ack = connection.recv_match(blocking=True, type="COMMAND_ACK", timeout=5)
    if ack and (ack.result==0):
        print(ack, f"BATTERY_STATUS set to {int(1000000/interval)}Hz", sep='\n')
    elif not ack:
        print("BATTERY_STATUS: Ack not received.")
    else:
        print("BATTERY_STATUS:", mavlink_results[ack.result], f'\nSystem {ack.target_system}, Component {ack.target_component}')
    connection.mav.command_long_send(
        connection.target_system, connection.target_component, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, 36, interval, 0, 0, 0, 0, 0, 0)
    ack = connection.recv_match(blocking=True, type="COMMAND_ACK", timeout=5)
    if ack and (ack.result==0):
        print(ack, f"SERVO_OUTPUT_RAW set to {int(1000000/interval)}Hz", sep='\n')
    elif not ack:
        print("SERVO_OUTPUT_RAW: Ack not received.")
    else:
        print("SERVO_OUTPUT_RAW:", mavlink_results[ack.result], f'\nSystem {ack.target_system}, Component {ack.target_component}')
    connection.mav.command_long_send(
        connection.target_system, connection.target_component, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, 74, interval, 0, 0, 0, 0, 0, 0)
    ack = connection.recv_match(blocking=True, type="COMMAND_ACK", timeout=5)
    if ack and (ack.result==0):
        print(ack, f"VFR_HUD set to {int(1000000/interval)}Hz", sep='\n')
    elif not ack:
        print("VFR_HUD: Ack not received.")
    else:
        print("VFR_HUD:", mavlink_results[ack.result], f'\nSystem {ack.target_system}, Component {ack.target_component}')
    connection.mav.command_long_send(
        connection.target_system, connection.target_component, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, 11030, interval, 0, 0, 0, 0, 0, 0)
    ack = connection.recv_match(blocking=True, type="COMMAND_ACK", timeout=5)
    if ack and (ack.result==0):
        print(ack, f"ESC_TELEMETRY_1_TO_4 set to {int(1000000/interval)}Hz", sep='\n')
    elif not ack:
        print("ESC_TELEMETRY_1_TO_4: Ack not received.")
    else:
        print("ESC_TELEMETRY_1_TO_4:", mavlink_results[ack.result], f'\nSystem {ack.target_system}, Component {ack.target_component}')
    print("MAVLink data rates set up.")
    connection.mav.command_long_send(
        connection.target_system, connection.target_component, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, 226, interval, 0, 0, 0, 0, 0, 0)
    ack = connection.recv_match(blocking=True, type="COMMAND_ACK", timeout=5)
    if ack and (ack.result==0):
        print(ack, f"RPM set to {int(1000000/interval)}Hz", sep='\n')
    elif not ack:
        print("RPM: Ack not received.")
    else:
        print("RPM:", mavlink_results[ack.result], f'\nSystem {ack.target_system}, Component {ack.target_component}')
    print("MAVLink data rates set up.")
    
def loop():
    global end
    throttle = 0
    current = 0
    current2 = 0
    voltage = 0
    voltage2 = 0
    rpm1 = 0
    rpm2 = 0
    charge = 0
    all = 0b00000000
    try:
        with open("FC_logs/list.txt", 'a') as file:
            print(log_file, file=file)
        with open(log_file, 'a') as file:
            print("Starting data logging.")
            while True:
                msg = connection.recv_match(blocking=True, type=["RC_CHANNELS", "BATTERY_STATUS", "SERVO_OUTPUT_RAW", "VFR_HUD", "ESC_TELEMETRY_1_TO_4", "RPM"])
                if not msg: continue
                # print(msg)
                if msg.get_type() == "BATTERY_STATUS":
                    if msg.temperature == 32767:
                        continue
                    voltage = msg.voltages[0]/1000
                    all = all | 0b00010000
                    current = msg.current_battery/100
                    all = all | 0b01000000
                    charge = msg.current_consumed
                    # print(msg)
                    all = all | 0b00000001
                elif msg.get_type() == "VFR_HUD":
                    throttle = msg.throttle
                    # print(f"VFR_HUD            : {throttle}")
                    all = all | 0b10000000
                elif msg.get_type() == "ESC_TELEMETRY_1_TO_4":
                    rpm2 = msg.rpm[2]
                    current2 = msg.current[2]/100
                    voltage2 = msg.voltage[2]/100
                    all = all | 0b00101010
                elif msg.get_type() == "SERVO_OUTPUT_RAW":
                    throttle = int((msg.servo3_raw-1000)/10)
                    # print(f"SERVO_OUTPUT_RAW       : {throttle}")
                    all = all | 0b10000000
                elif msg.get_type() == "RPM":
                    rpm1 = int(msg.rpm1)
                    all = all | 0b00000100
                data = f"{time.strftime("%Y-%m-%d %H:%M:%S")},{int(throttle)},{current},{current2},{voltage:.2f},{voltage2:.2f},{int(rpm1)},{int(rpm2)},{charge}"
                if all == 0b11111111:
                    print(data)
                    print(data, file=file)
                    all = 0
    except KeyboardInterrupt:
        end = True
        print("User terminated execution.")
        with open(log_file, 'a') as file:
            print(file=file)
        print("Logging ended.")
        connection.close()
        sys.exit(0)

if __name__ == "__main__":
    print("Setting up...")
    setup()
    print("Setup complete.")
    loop()
