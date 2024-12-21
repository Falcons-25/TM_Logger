import sys
import serial, serial.serialutil, serial.tools.list_ports
import time

def connect_arduino(port, baud) -> bool:
    global ser
    try:
        ser = serial.Serial(port=port, baudrate=baud)
        return True
    except serial.serialutil.SerialException:
        print("Error with arduino serial port.")
        return False

def setup():
    global ad, zero_load, calibration_factor, is_tared
    is_tared = False
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

    print(f"Serial COM : {serial_com}, {serial_baud}")
    s = input("Use last configuration? y/n: ")
    if s in 'Yy':
        pass
    else:
        comports = sorted([str(x) for x in serial.tools.list_ports.comports()])
        for (i, port) in enumerate(comports):
            print(f"{i+1}. {port}")
        serial_com = comports[int(input("Choose Serial COM Port: "))-1]
        serial_baud = int(input("Enter Serial port baud: "))
    a = connect_arduino(serial_com, serial_baud)
    if a:
        print("COM Port set up correctly.")
        with open("config.txt", 'w') as file:
            print(f"{serial_com},{serial_baud}", file=file)
            print(f"{mavlink_com},{mavlink_baud}", file=file)
            print(start_log_read, file=file)
            print(f"{motor}\n{esc}\n{batt}\n{prop}", file=file)
    else:
        print("Data inputs not initialised correctly.")
        print(f"Serial ({serial_com}): {a}")
        sys.exit(0)

    print("Calibrate load cell: Place vertical with no thrust")
    input()
    print("Taring...")
    d = []
    while len(d)<30:
        if ser.in_waiting:
            t = ser.readline().decode().strip()
            if t=="HX711 not found.":
                print(t)
                continue
            d.append(int(t))
            print(f"{len(d)}/30")
    print(d)
    print("30/30 values.")
    zero_load = int(sum(d)/len(d))
    calibration_factor = 1
    # calibration_factor = 394.312126
    calibration_factor = 390
    print(zero_load)
    print("Tared.")
    is_tared = True

def loop():
    thrust = 0
    try:
        log_file = f"Thrust_logs/Thrust_log_{time.strftime("%Y%m%d_%H%M%S")}.csv"
        with open("Thrust_logs/list.txt", 'a') as file:
            print(log_file, file=file)
        with open(log_file, 'a') as file:
            print("Starting data logging.")
            while True:
                try:
                    if ser.in_waiting:
                        # ser.reset_input_buffer()
                        line = int(ser.readline().decode().strip())
                        print(line)
                        thrust = int((line - zero_load)/calibration_factor)
                except UnicodeDecodeError:
                    continue
                except ValueError:
                    pass
                except KeyboardInterrupt:
                    raise KeyboardInterrupt()
                if thrust<0: thrust = 0
                data = f"{time.strftime("%Y-%m-%d %H:%M:%S")},{thrust}"
                print(data)
                print(data, file=file)
                time.sleep(0.01)
    except KeyboardInterrupt:
        with open(log_file, 'a') as file:
            print(file=file)
        print("User terminated execution.")
        print("Logging ended.")
        ser.close()
        sys.exit(0)

if __name__ == "__main__":
    print("Setting up...")
    setup()
    print("Setup complete.")
    loop()
