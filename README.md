# TM Logger

## Overview

The TM Logger project is designed to log and analyze telemetry data from motor and propeller testing. It comprises several Python scripts for data collection, processing, and logging.

## Folder Structure

- **`THRUST_LOGGER.PY`**: Connects to an Arduino to log thrust data from a load cell.
- **`FC_LOGGER.PY`**: Connects to a flight controller via MAVLink to log various telemetry data.
- **`COMPONENTS.TXT`**: Lists available components like propellers, ESCs, batteries, and motors.
- **`CONFIG.TXT`**: Contains configuration settings for serial/MAVLink connections and components under test.
- **`FC_LOGS/LIST.TXT`**: Tracks all flight controller log files.
- **`THRUST_LOGS/LIST.TXT`**: Tracks all thrust log files.
- **`DATAREADER.PY`**: Processes and combines logged data, writing summarized results to an Excel file.

## Usage

1. **Setup Configuration**
   Edit the `CONFIG.TXT` file to configure serial ports, MAVLink settings, and components being tested.

2. **Run Thrust Logger**
   Execute `THRUST_LOGGER.PY` to log thrust data from the load cell.

3. **Run FC Logger**
   Execute `FC_LOGGER.PY` to set up your testing configuration and start logging flight controller telemetry.

4. **Process Data**
   Execute `DATAREADER.PY` to summarize and export the combined data into an Excel file.

## Requirements

- **Python 3.x**
- **pymavlink**: [Installation Guide](https://mavlink.io/en/getting_started/py_mavlink.html)
- **pyserial**: Install via `pip install pyserial` ([Documentation](https://pythonhosted.org/pyserial/))
- **openpyxl**: Install via `pip install openpyxl` ([Documentation](https://openpyxl.readthedocs.io/en/stable/))

## Author

Sisir Lakkaraju
