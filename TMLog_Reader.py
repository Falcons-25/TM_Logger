import sys
import time
import csv
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import numpy as np
import statistics
from tabulate import tabulate
from openpyxl import load_workbook

def average(a: list|tuple) -> float:
    try:
        return sum(a)/len(a)
    except ZeroDivisionError:
        return -1

def unitary_average(a, b, req, key=0):
    lower = a[key]
    upper = b[key]
    out = [0]*len(a)
    for i in range(len(a)):
        out[i] = ((req-lower)*b[i] + (upper-req)*a[i])/(upper-lower)
    return out

def battery_percent(volt):
    a = int(123*(1-(1/((1+((volt/3.7)**80))**0.165))))
    return 100 if a>100 else 0 if a<0 else a

def setup():
    global all_tstamps, stm_fc_data, stm_thr_data, config, start_line, tm_type, file_timestamps, file_throttlestamps, file_speeds, file_tiny_summary, fc_log_file, thr_log_file, is_available, to_continue
    file_timestamps = "I:/My Drive/AssailingFalcons/Test Results/TM_Timestamps.xlsx"
    file_throttlestamps = "I:/My Drive/AssailingFalcons/Test Results/TM_Throttles.xlsx"
    file_tiny_summary = "I:/My Drive/AssailingFalcons/Test Results/New_TM.xlsx"
    file_speeds = "I:/My Drive/AssailingFalcons/Test Results/TM_Speeds.xlsx"
    all_tstamps = {}
    with open("config.txt", 'r') as file:
        conf = [x.strip() for x in file.readlines()]
        start_line = int(conf[2]) - 1
        fc_line = int(conf[7]) - 1
        thr_line = int(conf[8]) - 1
    with open("FC_logs/list.txt", 'r') as file:
        try:
            fc_log = file.readlines()[fc_line].strip()
            fc_log_type = fc_log.split(',')[0]
            fc_log_file = fc_log.split(',')[1]
            fc_log_read = []
            with open(fc_log_file, 'r') as file2:
                fc_log_read = [x.strip() for x in file2.readlines() if x.strip()]
        except Exception:
            print("No FC Logs remaining.")
            is_available = False
    with open("Thrust_logs/list.txt", 'r') as file:
        try:
            thr_log = file.readlines()[thr_line].strip()
            thr_log_type = thr_log.split(',')[0]
            thr_log_file = thr_log.split(',')[1]
        except Exception:
            print("No Thrust Logs remaining.")
            is_available = False
    print(f"FC_log: {fc_log_file}\nTh_log: {thr_log_file}")
    if fc_log_type != thr_log_type:
        print("FC and Thrust logs are not of the same type.")
        is_available = False
    else:
        tm_type = fc_log_type
    if not is_available:
        return
    config = [x.strip() for x in fc_log_read[0].split(',')]
    print(config)
    config[0] = time.strftime("%d-%b-%Y", time.strptime(config[0], "%Y-%m-%d %H:%M:%S"))
    stm_fc_data = fc_log_read[1:]
    print(f"{'\n'.join(config[1:])}")
    print(f"{tm_type} Test: {config[0]}")
    s = input("Continue? y/n: ")
    if s in 'Yy':
        print("Proceeding...")
    else:
        print("Exiting...")
        is_available = False
        to_continue = False
        return

def combine_stm_files():
    global stm_fc_data, stm_thr_data
    with open(fc_log_file, 'r') as file:
        stm_fc_data = [x.strip() for x in file.readlines()]
    with open(thr_log_file, 'r') as file:
        stm_thr_data = [x.strip() for x in file.readlines()]
    fc_start = time.strptime(stm_fc_data[1].split(',')[0], "%Y-%m-%d %H:%M:%S")
    thr_start = time.strptime(stm_thr_data[0].split(',')[0], "%Y-%m-%d %H:%M:%S")
    # print(len(stm_fc_data), len(stm_thr_data))
    if fc_start > thr_start:
        thr_start_t = 0
        for i, line in enumerate(stm_thr_data):
            if line.split(',')[0] == time.strftime("%Y-%m-%d %H:%M:%S", fc_start):
                thr_start_t = i
                break
        stm_thr_data[:] = stm_thr_data[thr_start_t:]
    elif thr_start > fc_start:
        fc_start_t = 1
        for i, line in enumerate(stm_fc_data[1:]):
            if line.split(',')[0] == time.strftime("%Y-%m-%d %H:%M:%S", thr_start):
                fc_start_t = i
                break
        stm_fc_data[:] = stm_fc_data[0:1] + stm_fc_data[fc_start_t-1:]
    # print(len(stm_fc_data), len(stm_thr_data))
    fc_end_i = stm_fc_data.index('', 1)
    thr_end_i = stm_thr_data.index('', 1)
    # print(stm_fc_data[fc_end_i-1].split(','))
    # print(stm_thr_data[thr_end_i-1].split(','))
    fc_end = time.strptime(stm_fc_data[fc_end_i-1].split(',')[0], "%Y-%m-%d %H:%M:%S")
    thr_end = time.strptime(stm_thr_data[thr_end_i-1].split(',')[0], "%Y-%m-%d %H:%M:%S")
    if fc_end > thr_end:
        fc_end_t = -1
        for i, line in enumerate(stm_fc_data[::-1]):
            if line.split(',')[0] == time.strftime("%Y-%m-%d %H:%M:%S", thr_end):
                fc_end_t = len(stm_fc_data) - i
                break
        stm_fc_data[:] = stm_fc_data[:fc_end_t]
    elif thr_end > fc_end:
        thr_end_t = -1
        for i, line in enumerate(stm_thr_data[::-1]):
            if line.split(',')[0] == time.strftime("%Y-%m-%d %H:%M:%S", fc_end):
                thr_end_t = len(stm_thr_data) - i
                break
        stm_thr_data[:] = stm_thr_data[:thr_end_t]
    stm_fc_data[:] = [x for x in stm_fc_data if x]
    stm_thr_data[:] = [x for x in stm_thr_data if x]

def summarise_stm_data():
    global final_tstamps, final_throttles, start_volt, end_volt, min_volt
    last_throttle = -1
    start_volt = end_volt = min_volt = 0
    start_charge = 0
    for line in stm_fc_data:
        if not line: continue
        values = line.split(',')
        if values[1].split()[0] in ["APC", "EMAX", "GemFan", "Generic", "HQ", "Orange", "GF"]: continue
        if values[0] not in all_tstamps.keys():
            all_tstamps[values[0]] = {"Throttle":[], "Thrust":[], "Current":[], "Current2":[], "Volt":[], "Volt2":[], "RPM1":[], "RPM2":[], "Capacity":[]}
        all_tstamps[values[0]]["Throttle"].append(int(values[1]))
        # all_tstamps[values[0]]["Thrust"].append(float(values[2]))
        all_tstamps[values[0]]["Current"].append(float(values[2]))
        all_tstamps[values[0]]["Current2"].append(float(values[3]))
        all_tstamps[values[0]]["Volt"].append(float(values[4]))
        all_tstamps[values[0]]["Volt2"].append(float(values[5]))
        all_tstamps[values[0]]["RPM1"].append(int(values[6]))
        all_tstamps[values[0]]["RPM2"].append(int(values[7]))
        all_tstamps[values[0]]["Capacity"].append(int(values[8]))

    for line in stm_thr_data:
        if not line: continue
        values = line.split(',')
        if values[0] not in all_tstamps.keys():
            print("Something is seriously wrong with your data.")
        else:
            all_tstamps[values[0]]["Thrust"].append(float(values[1]))

    thrust_tstamps = {}
    for line in stm_thr_data:
        values = [x.strip() for x in line.split(',')]
        if values[0] not in thrust_tstamps.keys():
            thrust_tstamps[values[0]] = []
        else:
            thrust_tstamps[values[0]].append(int(values[1]))

    # update averaged values for timestamps
    final_tstamps = {}
    for timestamp in all_tstamps:
        if len(final_tstamps) == 0:
            start_charge = min(all_tstamps[timestamp]["Capacity"])
        if timestamp not in final_tstamps.keys():
            final_tstamps[timestamp] = {"Throttle":[], "Thrust":[], "Current":[], "Current2":[], "Volt":[], "Volt2":[], "RPM1":[], "RPM2": [], "Capacity":[]}
        final_tstamps[timestamp]["Throttle"] = int(average(all_tstamps[timestamp]["Throttle"]))
        final_tstamps[timestamp]["Thrust"] = average(all_tstamps[timestamp]["Thrust"])
        final_tstamps[timestamp]["Current"] = average(all_tstamps[timestamp]["Current"])
        final_tstamps[timestamp]["Current2"] = average(all_tstamps[timestamp]["Current2"])
        final_tstamps[timestamp]["Volt"] = average(all_tstamps[timestamp]["Volt"])
        final_tstamps[timestamp]["Volt2"] = average(all_tstamps[timestamp]["Volt2"])
        final_tstamps[timestamp]["RPM1"] = int(average(all_tstamps[timestamp]["RPM1"]))
        final_tstamps[timestamp]["RPM2"] = int(average(all_tstamps[timestamp]["RPM2"]))
        final_tstamps[timestamp]["Capacity"] = int(average(all_tstamps[timestamp]["Capacity"])) - start_charge

    # update averaged values for throttle
    final_thr = []
    for timestamp in thrust_tstamps:
        m = len(thrust_tstamps[timestamp])
        n = len(all_tstamps[timestamp]["Throttle"])
        if not n: continue
        li = []
        for i in range(n):
            li.append(average(thrust_tstamps[timestamp][:]))
            # final_thr.append([all_tstamps[timestamp]["Throttle"][i], average(thrust_tstamps[timestamp][(i+m)//n:((i+m)//n)+1])])
            final_thr.append([
                all_tstamps[timestamp]["Throttle"][i],
                int(average(thrust_tstamps[timestamp][(i*m)//n : ((i+1)*m)//n])),
                all_tstamps[timestamp]["Current"][i],
                all_tstamps[timestamp]["Current2"][i],
                all_tstamps[timestamp]["Volt"][i],
                all_tstamps[timestamp]["Volt2"][i],
                all_tstamps[timestamp]["RPM1"][i],
                all_tstamps[timestamp]["Capacity"][i] - start_charge,
            ])
    final_throttles = []
    ls = {}
    for values in final_thr:
        # print(last_throttle, values[0])
        if last_throttle == values[0]:
            ls["Thrust"].append(values[1])
            ls["Current"].append(values[2])
            ls["Current2"].append(values[3])
            ls["Volt"].append(values[4])
            ls["Volt2"].append(values[5])
            ls["RPM1"].append(values[6])
            ls["Capacity"].append(values[7])
        else:
            if last_throttle==-1: pass
            else:
                final_throttles.append([
                    last_throttle,
                    int(average(ls["Thrust"])),
                    average(ls["Current"]),
                    average(ls["Current2"]),
                    average(ls["Volt"]),
                    average(ls["Volt2"]),
                    int(average(ls["RPM1"])),
                    int(average(ls["Capacity"])),
                ])
            last_throttle = values[0]
            ls["Thrust"] = [values[1]]
            ls["Current"] = [values[2]]
            ls["Current2"] = [values[3]]
            ls["Volt"] = [values[4]]
            ls["Volt2"] = [values[5]]
            ls["RPM1"] = [values[6]]
            ls["Capacity"] = [values[7]]
    final_throttles.append([0, 0, 0, 0, round(average(ls["Volt"]), 2), round(average(ls["Volt2"]), 2), 0, int(average(ls["Capacity"]))])
    start_volt = final_thr[0][4]
    end_volt = final_thr[-1][4]
    min_volt = min([x[4] for x in final_thr])

def summarise_stm_further():
    global preview, make_tiny_summary
    preview = []
    preview.append(final_throttles[0])
    search = [x[0] for x in final_throttles]
    if max(search)<90:
        make_tiny_summary = False
        return
    make_tiny_summary = True
    # 20-80
    for i in range(1, 5):
        if i*20 in search:
            preview.append(final_throttles[search.index(i*20)])
        else:
            j = 0
            low_ind = -1
            while low_ind==-1:
                j += 1
                try:
                    low_ind = search.index(i*20-j)
                except ValueError:
                    low_ind = -1
            preview.append(unitary_average(final_throttles[low_ind], final_throttles[low_ind+1], i*20))
    if 100 in search:
        preview.append(final_throttles[search.index(100)])
    elif 99 in search:
        preview.append(final_throttles[search.index(99)])
    elif 98 in search:
        preview.append(final_throttles[search.index(98)])
    else:
        preview.append(final_throttles[search.index(max(search))])
    print(tabulate(preview, headers=["Throttle", "Thrust", "Current", "Current2", "Volt", "Volt2", "RPM1", "Capacity",], tablefmt="simple_grid"))

def write_stm_to_files():
    global is_available, to_continue
    name = 'S' + config[0]
    wb1 = load_workbook(file_timestamps)
    if name in wb1:
        ws1 = wb1[name]
    else:
        ws1 = wb1.create_sheet(name)
    wb1.active = ws1
    start_row = ws1.max_row + 3 if ws1.max_row>1 else 2
    
    ws1.cell(row=start_row+0, column=2).value = f"{config[2]}"
    ws1.merge_cells(start_column=2, start_row=start_row, end_column=12, end_row=start_row)
    ws1.cell(row=start_row+1, column=2).value = f"({tm_type}) {config[0]}"
    ws1.merge_cells(start_column=2, start_row=start_row+1, end_column=12, end_row=start_row+1)
    ws1.cell(row=start_row+2, column=2).value = f"{config[1]}"
    ws1.merge_cells(start_column=2, start_row=start_row+2, end_column=12, end_row=start_row+2)
    ws1.cell(row=start_row+3, column=2).value = f"{config[3]}"
    ws1.merge_cells(start_column=2, start_row=start_row+3, end_column=12, end_row=start_row+3)
    ws1.cell(row=start_row+4, column=2).value = f"{config[4]}"
    ws1.merge_cells(start_column=2, start_row=start_row+4, end_column=12, end_row=start_row+4)
    batt_data = f"{battery_percent(start_volt/4)}% {start_volt:.2f}V  ->  {battery_percent(end_volt/4)}% {end_volt:.2f}V  (100% = {battery_percent(min_volt/4)}% {min_volt:.2f}V)"
    print(batt_data)
    ws1.cell(row=start_row+5, column=2).value = batt_data
    ws1.merge_cells(start_column=2, start_row=start_row+5, end_column=12, end_row=start_row+5)
    ws1.merge_cells(start_column=2, start_row=start_row+6, end_column=12, end_row=start_row+6)
    ws1.cell(row=start_row+7, column=2).value = "Timestamp"
    ws1.cell(row=start_row+7, column=3).value = "Throttle (%)"
    ws1.cell(row=start_row+7, column=4).value = "Thrust (gf)"
    ws1.cell(row=start_row+7, column=5).value = "Current (A)"
    ws1.cell(row=start_row+7, column=6).value = "Power (W)"
    ws1.cell(row=start_row+7, column=7).value = "Volt (V)"
    ws1.cell(row=start_row+7, column=8).value = "Current2 (A)"
    ws1.cell(row=start_row+7, column=9).value = "Volt2 (V)"
    ws1.cell(row=start_row+7, column=10).value = "RPM1"
    ws1.cell(row=start_row+7, column=11).value = "Capacity (mAh)"
    ws1.cell(row=start_row+7, column=12).value = "Thrust/Current"
    wb1.save(file_timestamps)
    
    for i, tstamp in enumerate(final_tstamps.keys()):
        ws1.cell(row=start_row+i, column=2).value = tstamp
        ws1.cell(row=start_row+i, column=3).value = int(final_tstamps[tstamp]["Throttle"])
        ws1.cell(row=start_row+i, column=4).value = int(final_tstamps[tstamp]["Thrust"])
        ws1.cell(row=start_row+i, column=5).value = round(final_tstamps[tstamp]["Current"], 2)
        ws1.cell(row=start_row+i, column=6).value = round(final_tstamps[tstamp]["Current"]*final_tstamps[tstamp]["Volt"], 2)
        ws1.cell(row=start_row+i, column=7).value = round(final_tstamps[tstamp]["Volt"], 2)
        ws1.cell(row=start_row+i, column=8).value = round(final_tstamps[tstamp]["Current2"], 2)
        ws1.cell(row=start_row+i, column=9).value = round(final_tstamps[tstamp]["Volt2"], 2)
        ws1.cell(row=start_row+i, column=10).value = int(final_tstamps[tstamp]["RPM1"])
        ws1.cell(row=start_row+i, column=11).value = int(final_tstamps[tstamp]["Capacity"])
        ws1.cell(row=start_row+i, column=12).value = round(final_tstamps[tstamp]["Thrust"]/final_tstamps[tstamp]["Current"], 6) if final_tstamps[tstamp]["Current"] else 0
    wb1.save(file_timestamps)
    wb1.close()
    print("Timestamped data saved to file.")

    wb2 = load_workbook(file_throttlestamps)
    if name in wb2:
        ws2 = wb2[name]
    else:
        ws2 = wb2.create_sheet(name)
    wb2.active = ws2
    start_row = ws2.max_row + 3
    if start_row==4:
        start_row = 2
    ws2.cell(row=start_row+0, column=2).value = f"{config[2]}"
    ws2.merge_cells(start_column=2, start_row=start_row, end_column=11, end_row=start_row)
    ws2.cell(row=start_row+1, column=2).value = f"({tm_type}) {config[0]}"
    ws2.merge_cells(start_column=2, start_row=start_row+1, end_column=11, end_row=start_row+1)
    ws2.cell(row=start_row+2, column=2).value = f"{config[1]}"
    ws2.merge_cells(start_column=2, start_row=start_row+2, end_column=11, end_row=start_row+2)
    ws2.cell(row=start_row+3, column=2).value = f"{config[3]}"
    ws2.merge_cells(start_column=2, start_row=start_row+3, end_column=11, end_row=start_row+3)
    ws2.cell(row=start_row+4, column=2).value = f"{config[4]}"
    ws2.merge_cells(start_column=2, start_row=start_row+4, end_column=11, end_row=start_row+4)
    ws2.cell(row=start_row+5, column=2).value = batt_data
    ws2.merge_cells(start_column=2, start_row=start_row+5, end_column=11, end_row=start_row+5)
    ws2.merge_cells(start_column=2, start_row=start_row+6, end_column=11, end_row=start_row+6)
    ws2.cell(row=start_row+7, column=2).value = "Throttle (%)"
    ws2.cell(row=start_row+7, column=3).value = "Thrust (gf)"
    ws2.cell(row=start_row+7, column=4).value = "Current (A)"
    ws2.cell(row=start_row+7, column=5).value = "Power (W)"
    ws2.cell(row=start_row+7, column=6).value = "Volt (V)"
    ws2.cell(row=start_row+7, column=7).value = "Current2 (A)"
    ws2.cell(row=start_row+7, column=8).value = "Volt2 (V)"
    ws2.cell(row=start_row+7, column=9).value = "RPM1"
    ws2.cell(row=start_row+7, column=10).value = "Capacity (mAh)"
    ws2.cell(row=start_row+7, column=11).value = "Thrust/Current"
    start_row = start_row + 8
    wb2.save(file_throttlestamps)

    for i, tstamp in enumerate(final_throttles):
        ws2.cell(row=start_row+i, column=2).value = int(tstamp[0])
        ws2.cell(row=start_row+i, column=3).value = int(tstamp[1])
        ws2.cell(row=start_row+i, column=4).value = round(tstamp[2], 2)
        ws2.cell(row=start_row+i, column=5).value = round(tstamp[2]*tstamp[4], 2)
        ws2.cell(row=start_row+i, column=6).value = round(tstamp[4], 2)
        ws2.cell(row=start_row+i, column=7).value = round(tstamp[3], 2)
        ws2.cell(row=start_row+i, column=8).value = round(tstamp[5], 2)
        ws2.cell(row=start_row+i, column=9).value = int(tstamp[6])
        ws2.cell(row=start_row+i, column=10).value = int(tstamp[7])
        ws2.cell(row=start_row+i, column=11).value = round(tstamp[1]/tstamp[2], 6) if tstamp[2] else 0
    wb2.save(file_throttlestamps)
    wb2.close()
    print("Throttle-stamped data saved to file.")

def write_tiny_stm_summary():
    name = 'S' + config[0]
    wb = load_workbook(file_tiny_summary)
    if name in wb:
        ws = wb[name]
    else:
        ws = wb.create_sheet(name)
    wb.active = ws
    start_row = ws.max_row + 3
    if start_row==4:
        start_row = 2
    ws.cell(row=start_row+0, column=2).value = f"{config[2]}"
    ws.merge_cells(start_column=2, start_row=start_row, end_column=6, end_row=start_row)
    ws.cell(row=start_row+1, column=2).value = f"({tm_type}) {config[0]}"
    ws.merge_cells(start_column=2, start_row=start_row+1, end_column=6, end_row=start_row+1)
    ws.cell(row=start_row+2, column=2).value = f"{config[1]}"
    ws.merge_cells(start_column=2, start_row=start_row+2, end_column=6, end_row=start_row+2)
    ws.cell(row=start_row+3, column=2).value = f"{config[3]}"
    ws.merge_cells(start_column=2, start_row=start_row+3, end_column=6, end_row=start_row+3)
    ws.cell(row=start_row+4, column=2).value = f"{config[4]}"
    ws.merge_cells(start_column=2, start_row=start_row+4, end_column=6, end_row=start_row+4)
    ws.cell(row=start_row+5, column=2).value = f"{battery_percent(start_volt/4)}% {start_volt:.2f}V  ->  {battery_percent(end_volt/4)}% {end_volt:.2f}V  (100% = {battery_percent(min_volt/4)}% {min_volt:.2f}V)"
    ws.merge_cells(start_column=2, start_row=start_row+5, end_column=6, end_row=start_row+5)
    ws.merge_cells(start_column=2, start_row=start_row+6, end_column=6, end_row=start_row+6)
    ws.cell(row=start_row+7, column=2).value = "Throttle (%)"
    ws.cell(row=start_row+7, column=3).value = "Thrust (gf)"
    ws.cell(row=start_row+7, column=4).value = "Current (A)"
    ws.cell(row=start_row+7, column=5).value = "Power (W)"
    ws.cell(row=start_row+7, column=6).value = "Volt (V)"
    start_row = start_row + 8
    wb.save(file_tiny_summary)
    # throttle, thrust, current, current2, volt, volt2, rpm1, capacity
    for i, tval in enumerate(preview):
        ws.cell(row=start_row+i, column=2).value = int(tval[0])
        ws.cell(row=start_row+i, column=3).value = int(tval[1])
        ws.cell(row=start_row+i, column=4).value = round(tval[2], 2)
        ws.cell(row=start_row+i, column=5).value = round(tval[2]*tval[4], 2)
        ws.cell(row=start_row+i, column=6).value = round(tval[4], 2)
    wb.save(file_tiny_summary)
    wb.close()
    print("Tiny summary saved to file.")

def update_config():
    global to_continue, is_available
    conf = fc = th = ""
    with open("config.txt", 'r') as file:
        conf = [x.strip() for x in file.readlines()]
        fc = int(conf[7]) + 1
        th = int(conf[8]) + 1
    with open("config.txt", 'w') as file:
        print('\n'.join(conf[:-2]), file=file)
        print(fc, file=file)
        print(th, file=file)
        print("Configuration file updated.")
    with open("FC_logs/list.txt", 'r') as file:
        fclen = len([x.strip() for x in file.readlines() if x.strip()])
    with open("Thrust_logs/list.txt", 'r') as file:
        thlen = len([x.strip() for x in file.readlines() if x.strip()])
    if (fclen<fc) and (thlen<th):
        to_continue = False
        is_available = False
    else:
        print(f"{fclen-fc+1} log{'' if (fclen-fc+1)==1 else 's'} remaining.")

def read_and_average_dtm_thr_file(file_path) -> dict:
    data = defaultdict(list)
    with open(file_path, newline='') as f:
        reader = csv.reader(f)
        i = 0
        for row in reader:
            if (not i) or (not row):
                i += 1
                continue
            timestamp, value = row[0], float(row[1])
            data[timestamp].append(value)
    return {ts: sum(vals)/len(vals) for ts, vals in data.items()}

def read_and_average_dtm_fc_file(file_path) -> dict:
    data = defaultdict(list)
    with open(file_path, newline='') as f:
        reader = csv.reader(f)
        i = 0
        for row in reader:
            if (not i) or (not row):
                i += 1
                continue
            timestamp = row[0]
            values = list(map(float, row[1:]))
            data[timestamp].append(values)
    result = {}
    for ts, all_vals in data.items():
        transposed = list(zip(*all_vals))
        averaged = [sum(col)/len(col) for col in transposed]
        result[ts] = averaged
    return result

def combine_dtm_files(thr_dict, fc_dict) -> dict:
    combined = {}
    common_keys = set(thr_dict) & set(fc_dict)
    for ts in sorted(common_keys):
        # if thr_dict[ts] < 220:
            # continue
        combined[ts] = fc_dict[ts][:1] + [thr_dict[ts]] + fc_dict[ts][1:]
    return combined

def dict_to_sorted_list(combined_dict) -> list:
    data_list = [[ts] + vals for ts, vals in combined_dict.items()]
    data_list = [x for x in data_list if x[-1]>=5.5]
    return sorted(data_list, key=lambda x: x[-1])

def smooth_data_by_value(data_list, key_index=1, value_index=0, do_all=False, radius=0.1, step=0.2) -> list:
    """
    Smooths data by averaging values within a given radius around a center point.
    If do_all is True, it smooths all parameters in each element individually.
    combi: ['2025-05-04 11:05:15', 54.6, 342.7439024390244, 5.392, 5.398000000000001, 15.986, 15.982, 11932.4, 11901.2, 7.6, 5.645669746398926]
    data_list = [342.7439024390244, 5.392, 5.398000000000001, 15.986, 15.982, 11932.4, 11901.2, 7.6, 5.645669746398926]
    """
    values = [row[key_index] for row in data_list]
    min_val, max_val = min(values), max(values)
    if do_all:
        smoothed = []
        for i in range(len(data_list[0])):
            if i==key_index: continue
            s = [row[i] for row in data_list if type(row[i]) != str]
            if s:
                center = round(min_val / step) * step
                t = []
                while center <= max_val:
                    group = [row[i] for row in data_list if abs(row[key_index] - center) <= radius]
                    if group:
                        t.append([center, sum(group) / len(group)])
                    else:
                        group = [row[i] for row in data_list if abs(row[key_index] - center) <= 2*radius]
                        if group:
                            t.append([center, sum(group) / len(group)])
                        else:
                            group = [row[i] for row in data_list if abs(row[key_index] - center) <= 3*radius]
                            if group:
                                t.append([center, sum(group) / len(group)])
                            else:
                                t.append([center, float('nan')])
                    # clean up nans as weighted avg of prev and next
                    center = round((center + step) / step) * step
                if smoothed:
                    for i in range(len(smoothed)):
                        smoothed[i].append(t[i][1])
                else:
                    smoothed = t.copy()
        return smoothed
    smoothed = []
    center = round(min_val / step) * step
    while center <= max_val:
        group = [row[value_index] for row in data_list if abs(row[key_index] - center) <= radius]
        if group:
            smoothed.append([center, sum(group) / len(group)])
        center = round((center + step) / step) * step
    return smoothed

def average_by_key(data_list, key_index, value_index, step=0.01, radius=None) -> dict:
    """
    Groups values by rounding the key (e.g., airspeed) to given step and averages associated values.
    If radius is given, it includes values within ±radius instead of strict binning.
    """
    values = [row[key_index] for row in data_list]
    min_val, max_val = min(values), max(values)
    
    averaged = {}
    center = round(min_val / step) * step
    while center <= max_val:
        if radius is None:
            group = [row[value_index] for row in data_list if round(row[key_index] / step) * step == center]
        else:
            group = [row[value_index] for row in data_list if abs(row[key_index] - center) <= radius]
        if group:
            averaged[center] = round(sum(group)/len(group), 2)
        center = round((center + step) / step) * step
    return averaged

def mean_deviation_against_reference(original_list, smoothed_list, x_index, y_index) -> float:
    smoothed_dict = {row[0]:row[1] for row in smoothed_list}
    diffs = []
    for row in original_list:
        x = round(row[x_index], 2)
        if x in smoothed_dict:
            y_actual = row[y_index]
            y_smooth = smoothed_dict[x]
            diffs.append(abs(y_actual - y_smooth))
    return sum(diffs) / len(diffs) if diffs else 0.0

def stddev_against_reference(original_list, smoothed_list, x_index, y_index) -> float:
    try:
        smoothed_dict = {row[0]:row[1] for row in smoothed_list}
    except ValueError as e:
        print(smoothed_list)
        raise e
    diffs = []
    for row in original_list:
        x = round(row[x_index], 2)
        if x in smoothed_dict:
            y_actual = row[y_index]
            y_smooth = smoothed_dict[x]
            diffs.append(y_actual - y_smooth)
    return statistics.stdev(diffs) if len(diffs) > 1 else 0.0

def find_min_mdev(original, smoothed, min_radius, max_radius, min_step, max_step, x_index, y_index) -> tuple[list[float, float], list[float, float]]:
    min_mdev = [0, 0, float('inf')]
    max_mdev = [0, 0, 0]
    for r in range(int(min_radius * 10), int(max_radius * 10) + 1):
        for s in range(int(min_step * 100), int(max_step * 100) + 1):
            smooth_list = smooth_data_by_value([x[2:] for x in original], key_index=8, value_index=0, radius=r/10, step=s/100, do_all=False)
            mdev = mean_deviation_against_reference(original, smooth_list, x_index=10, y_index=2)
            if mdev == 0:
                continue
            if mdev < min_mdev[2]:
                min_mdev = [r/10, s/100, mdev]
            if mdev > max_mdev[2]:
                max_mdev = [r/10, s/100, mdev]
    return min_mdev, max_mdev

def find_static_thrust(motor, prop, throttle) -> float:
    fclist = []
    thlist = []
    # separate dynamic from static logs somehow
    with open(r"FC_logs/list.txt", "r") as file1:
        # fclist = [x.strip() for x in file1.readlines() if ("20250504" not in x and "20250211" not in x)]
        fclist = [x.split(',')[1].strip() for x in file1.readlines() if x.split(',')[0].lower()=='static']
    with open(r"Thrust_logs/list.txt", "r") as file2:
        # thlist = [x.strip() for x in file2.readlines() if ("20250504" not in x and "20250211" not in x)]
        thlist = [x.split(',')[1].strip() for x in file2.readlines() if x.split(',')[0].lower()=='static']

    if len(fclist) != len(thlist):
        print("Error: The number of FC logs and Thrust logs do not match.")
        return 0

    files = {}
    for i in range(len(fclist)):
        with open(f"{fclist[i]}", "r") as file3:
            # [prop, motor, esc, batt]
            conf = file3.readline().strip().split(",")[1:]
            if conf[:2] == [prop, motor]:
                files[i] = (fclist[i], thlist[i])

    if not files:
        print("No matching files found.")
        return 0

    found_thr = []

    for i in files:
        with open(files[i][0], "r") as file3:
            fc_lines = [x.strip() for x in file3.readlines()][1:]
            lines = [line.split(",") for line in fc_lines if line]
            ts = [x[0] for x in lines if int(x[1]) in range(throttle-3, throttle+3)]
            if not ts:
                print(f"No timestamp data found for {throttle}% in {files[i][0]}")
                continue
        with open(files[i][1], "r") as file4:
            th_lines = [x.strip() for x in file4.readlines()][1:]
            lines = [line.split(",") for line in th_lines if line and line.split(",")[0] in ts]
            d = {}
            for item in lines:
                if item[0] in d:
                    d[item[0]].append(int(item[1]))
                else:
                    d[item[0]] = [int(item[1])]
            for item in d:
                d[item] = average(d[item])
            thrust = [d[x] for x in ts if x in d]
            if not thrust:
                print(f"No thrust data found for {throttle}% in {files[i][1]}")
                continue
            found_thr.append(average(thrust))

    return average(found_thr)

def find_static_parameter(motor, prop, throttle, param="thrust") -> float:
    if param == "thrust":
        return find_static_thrust(motor, prop, throttle)
    elif param.lower() in ["current1", "current2", "volt1", "volt2", "rpm1", "rpm2"]:
        fclist = []
        with open(r"FC_logs/list.txt", "r") as file1:
            # fclist = [x.strip() for x in file1.readlines() if ("20250504" not in x and "20250211" not in x)]
            fclist = [x.split(',')[1].strip() for x in file1.readlines() if x.split(',')[0].lower()=='static']
        files = []
        for i in fclist:
            with open(f"{i}", "r") as file2:
                # [prop, motor, esc, batt]
                conf = file2.readline().strip().split(",")[1:]
                if conf[:2] == [prop, motor]:
                    files.append(i)
        if not files:
            print("No matching files found.")
            return 0
        
        parm = []
        for i in files:
            with open(f"{i}", "r") as file3:
                fc_lines = [x.strip().split(',') for x in file3.readlines() if x.strip()][1:]
                lines = [line for line in fc_lines if line and int(line[1]) in range(throttle-3, throttle+3)]
                found_parm1 = []
                if not lines:
                    print(f"No timestamp data found for {throttle}% in {i}")
                    continue
                if param.lower() == "current1":
                    found_parm1 = [float(x[2]) for x in lines]
                if param.lower() == "current2":
                    found_parm1 = [float(x[3]) for x in lines]
                elif param.lower() == "volt1":
                    found_parm1 = [float(x[4]) for x in lines]
                elif param.lower() == "volt2":
                    found_parm1 = [float(x[5]) for x in lines]
                elif param.lower() == "rpm1":
                    found_parm1 = [float(x[6]) for x in lines]
                elif param.lower() == "rpm2":
                    found_parm1 = [float(x[7]) for x in lines]
                parm1 = average(found_parm1)
                if not parm1:
                    print(f"No {param} data found for {throttle}% in {i}")
                    continue
                print(parm1)
                parm.append(parm1)
        if not parm:
            print(f"No {param} data found for {throttle}% in any file.")
            return 0
        return average(parm)
    else:
        print(f"Unknown parameter: {param}")
        return 0

def extrapolate_to_zero(available_points, known_y_at_zero, num_points=15, include_known_zero=True, step=0.1, x_index=0, y_index=1) -> list:
    fit_points = available_points[:num_points]
    x_vals = [row[x_index] for row in fit_points]
    # print("\n".join([str(x) for x in fit_points]))
    try:
        y_vals = [row[y_index] for row in fit_points]
        # print(f"Y_vals: {y_vals}")
    except IndexError as e:
        print(y_index)
        print(fit_points[0])
        print(fit_points[1])
        print(fit_points[y_index])
        raise e

    q = np.arange(0, min(x_vals), step)
    if include_known_zero:
        x_vals.append(0)
        y_vals.append(known_y_at_zero)
    coeffs = np.polyfit(x_vals, y_vals, deg=3)
    a, b, c, d = coeffs
    extrapolated_x = q
    extrapolated_y = a * extrapolated_x**3 + b * extrapolated_x**2 + c * extrapolated_x + d

    extrapolated = [list(x) for x in zip(extrapolated_x.tolist(), extrapolated_y.tolist())]
    return extrapolated

def make_dtm_summary(dtm_data_dict, max_airspeed) -> list:
    summary_list = []
    for i in range(max_airspeed+1):
        if i > max(dtm_data_dict.keys()):
            break
        summary_list.append([i])
        for j in dtm_data_dict[i]:
            summary_list[-1].append(float(j))
    return summary_list

def resample(data=[], step=0.2, key=0) -> list:
    if not data:
        return []
    sampled = []
    low = 0
    keys = [x[key] for x in data]
    for i in range(int(max(keys)/step) + 1):
        if not ((round(keys[low], 2) <= i*step <= round(keys[low+1], 2))):
            low += 1
            if low >= len(keys):
                break
        sampled.append(unitary_average(data[low], data[low+1], i*step, key=key))
    return sampled

def write_dtm_to_file(summarised_data, test_throttle) -> None:
    name = 'D' + config[0]
    wb1 = load_workbook(file_speeds)
    if name in wb1:
        ws1 = wb1[name]
    else:
        ws1 = wb1.create_sheet(name)
    wb1.active = ws1
    start_row = ws1.max_row + 3 if ws1.max_row > 1 else 2

    ws1.cell(row=start_row+0, column=2).value = f"{config[2]}"
    ws1.merge_cells(start_column=2, start_row=start_row, end_column=11, end_row=start_row)
    ws1.cell(row=start_row+1, column=2).value = f"(Dynamic: {test_throttle}%) {config[0]}"
    ws1.merge_cells(start_column=2, start_row=start_row+1, end_column=11, end_row=start_row+1)
    ws1.cell(row=start_row+2, column=2).value = f"{config[1]}"
    ws1.merge_cells(start_column=2, start_row=start_row+2, end_column=11, end_row=start_row+2)
    ws1.cell(row=start_row+3, column=2).value = f"{config[3]}"
    ws1.merge_cells(start_column=2, start_row=start_row+3, end_column=11, end_row=start_row+3)
    ws1.cell(row=start_row+4, column=2).value = f"{config[4]}"
    ws1.merge_cells(start_column=2, start_row=start_row+4, end_column=11, end_row=start_row+4)
    ws1.merge_cells(start_column=2, start_row=start_row+5, end_column=11, end_row=start_row+5)
    ws1.cell(row=start_row+6, column=2).value = "Airspeed (m/s)"
    ws1.cell(row=start_row+6, column=3).value = "Thrust (gf)"
    ws1.cell(row=start_row+6, column=4).value = "Current (A)"
    ws1.cell(row=start_row+6, column=5).value = "Power (W)"
    ws1.cell(row=start_row+6, column=6).value = "Volt (V)"
    ws1.cell(row=start_row+6, column=7).value = "Current2 (A)"
    ws1.cell(row=start_row+6, column=8).value = "Volt2 (V)"
    ws1.cell(row=start_row+6, column=9).value = "RPM1"
    ws1.cell(row=start_row+6, column=10).value = "RPM2"
    ws1.cell(row=start_row+6, column=11).value = "Thrust/Current (gf/A)"
    start_row += 7
    wb1.save(file_speeds)

    for i, item in enumerate(summarised_data):
        ws1.cell(row=start_row+i, column=2).value = f"{int(item[0])}"
        ws1.cell(row=start_row+i, column=3).value = f"{round(item[1])}"
        ws1.cell(row=start_row+i, column=4).value = f"{round(item[2], 2):.2f}"
        ws1.cell(row=start_row+i, column=5).value = f"{round(item[2] * item[4], 2):.2f}"
        ws1.cell(row=start_row+i, column=6).value = f"{round(item[4], 2):.2f}"
        ws1.cell(row=start_row+i, column=7).value = f"{round(item[3], 2):.2f}"
        ws1.cell(row=start_row+i, column=8).value = f"{round(item[5], 2):.2f}"
        ws1.cell(row=start_row+i, column=9).value = f"{round(item[6])}"
        ws1.cell(row=start_row+i, column=10).value = f"{round(item[7])}"
        ws1.cell(row=start_row+i, column=11).value = f"{(round(item[1] / item[2], 7) if (item[2] != 0) else 0):.7f}"
    wb1.save(file_speeds)
    wb1.close()
    print("Dynamic data written to file.")

def write_tiny_summary(summarised_data, test_throttle) -> None:
    wb2 = load_workbook(file_tiny_summary)
    name = 'D' + config[0]
    if name in wb2:
        ws2 = wb2[name]
    else:
        ws2 = wb2.create_sheet(name)
    ws2 = wb2.active
    start_row = ws2.max_row + 3 if ws2.max_row > 1 else 2

    ws2.cell(row=start_row+0, column=2).value = f"{config[2]}"
    ws2.merge_cells(start_column=2, start_row=start_row, end_column=6, end_row=start_row)
    ws2.cell(row=start_row+1, column=2).value = f"(Dynamic: {test_throttle}%) {config[0]}"
    ws2.merge_cells(start_column=2, start_row=start_row+1, end_column=6, end_row=start_row+1)
    ws2.cell(row=start_row+2, column=2).value = f"{config[1]}"
    ws2.merge_cells(start_column=2, start_row=start_row+2, end_column=6, end_row=start_row+2)
    ws2.cell(row=start_row+3, column=2).value = f"{config[3]}"
    ws2.merge_cells(start_column=2, start_row=start_row+3, end_column=6, end_row=start_row+3)
    ws2.cell(row=start_row+4, column=2).value = f"{config[4]}"
    ws2.merge_cells(start_column=2, start_row=start_row+4, end_column=6, end_row=start_row+4)
    ws2.merge_cells(start_column=2, start_row=start_row+5, end_column=6, end_row=start_row+5)
    ws2.cell(row=start_row+6, column=2).value = "Airspeed (m/s)"
    ws2.cell(row=start_row+6, column=3).value = "Thrust (gf)"
    ws2.cell(row=start_row+6, column=4).value = "Current (A)"
    ws2.cell(row=start_row+6, column=5).value = "RPM"
    ws2.cell(row=start_row+6, column=6).value = "Thrust/Current (gf/A)"
    start_row += 7
    wb2.save(file_tiny_summary)

    skip = 0
    for i, item in enumerate(summarised_data):
        if item[0]<5:
            skip += 1
            continue
        ws2.cell(row=start_row+i-skip, column=2).value = int(item[0])
        ws2.cell(row=start_row+i-skip, column=3).value = round(item[1], 2)
        ws2.cell(row=start_row+i-skip, column=4).value = round(item[2], 2)
        ws2.cell(row=start_row+i-skip, column=5).value = round(item[6])
        ws2.cell(row=start_row+i-skip, column=6).value = round(item[1] / item[2], 7) if (item[2] != 0) else 0

    wb2.save(file_tiny_summary)
    wb2.close()
    print("Tiny summary written to file.")

def display_graphs(*args, titles=None, colours=None) -> None:
    # x_orig = [row[-1] for row in combi_list]
    # y_orig = [row[2] for row in combi_list]

    # x_smdev = [row[0] for row in smooth_mdev]
    # y_smdev = [row[1] for row in smooth_mdev]

    # x_rsmdev = [row[0] for row in resmooth_mdev]
    # y_rsmdev = [row[1] for row in resmooth_mdev]

    # x_final = [row[0] for row in smooth_final]
    # y_final = [row[1] for row in smooth_final]

    plt.figure(figsize=(8, 5))
    for i, arg in enumerate(args):
        x = [row[0] for row in arg]
        y = [row[1] for row in arg]
        if not titles:
            title = f"Data {i+1}"
        else:
            title = titles[i] if i < len(titles) else f"Data {i+1}"
        if not colours:
            colour = 'blue'
        else:
            colour = colours[i] if i < len(colours) else None
        plt.plot(x, y, '-o', color=colour, label=title, alpha=0.4)
    # plt.plot(x_orig, y_orig, 'o', alpha=0.4, label="Original Data")
    # plt.plot(x_smdev, y_smdev, '-o', color='green', label="Smoothed Data", alpha=0.4)
    # plt.plot(x_rsmdev, y_rsmdev, '-o', color='red', label="ReSmoothed Data", alpha=0.4)
    # plt.plot(x_final, y_final, '-o', color='black', label="Final Data", alpha=0.4)
    plt.xlabel("Airspeed (m/s)")
    plt.ylabel("Thrust (gf)")
    plt.title("Thrust vs Airspeed")
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    is_available = True
    to_continue = True
    s = input("Write to files? y/n: ")
    if s in 'Yy': write_to_files = True
    else: write_to_files = False
    while is_available and to_continue:
        print("Setting up...")
        setup()
        if not is_available:
            continue
        print("Setup complete.")
        print()
        if tm_type == "Static":
            combine_stm_files()
            summarise_stm_data()
            if write_to_files: write_stm_to_files()
            else: print("Skipped: Write STM results to file.")
            summarise_stm_further()
            if make_tiny_summary:
                if write_to_files: write_tiny_stm_summary()
                else: print("Skipped: Write STM summary to file.")
            update_config()
            if is_available:
                s = input("Continue? y/n: ")
                if s in 'Yy':
                    to_continue = True
                    print()
                else:
                    to_continue = False
            else:
                to_continue = False
        elif tm_type == "Dynamic":
            dtm_fc_data = read_and_average_dtm_fc_file(fc_log_file)
            dtm_thr_data = read_and_average_dtm_thr_file(thr_log_file)
            comined_dtm_dict = combine_dtm_files(dtm_thr_data, dtm_fc_data)
            combined_dtm_list = dict_to_sorted_list(comined_dtm_dict)
            # 0timestamp, 1throttle, 2thrust, 3curr1, 4curr2, 5volt1, 6volt2, 7rpm1, 8rpm2, 9charge, 10airspeed
            throttle_list = Counter([int(row[1]) for row in combined_dtm_list])
            test_throttle = max(throttle_list, key=throttle_list.get)
            print(f"Test throttle: {test_throttle}%")
            start_time = time.perf_counter()
            min_mdev, max_mdev = find_min_mdev(
                combined_dtm_list, [], min_radius=0.1, max_radius=4,min_step=0.01, max_step=1, x_index=8, y_index=2)
            print(f"Time taken: {time.perf_counter() - start_time:.2f}s")
            print(f"Minimum mean deviation: {min_mdev}")
            print(f"Maximum mean deviation: {max_mdev}")
            if min_mdev[2] == float('inf'):
                break
            smooth_mdev = smooth_data_by_value([row[2:] for row in combined_dtm_list], key_index=8, radius=min_mdev[0], step=min_mdev[1], do_all=True)
            resmooth_mdev = smooth_data_by_value(smooth_mdev, key_index=0, radius=4, step=0.2, do_all=True)
            smooth_extrapolated = extrapolate_to_zero(smooth_mdev, known_y_at_zero=find_static_thrust(config[2], config[1], test_throttle), num_points=15, include_known_zero=True, step=min_mdev[1], x_index=0, y_index=1)
            resmooth_extrapolated = extrapolate_to_zero(resmooth_mdev, known_y_at_zero=find_static_thrust(config[2], config[1], test_throttle), num_points=15, include_known_zero=True, step=0.2, x_index=0, y_index=1)
            extra_s = len(smooth_extrapolated)
            extra_r = len(resmooth_extrapolated)
            smooth_mdev = smooth_extrapolated + smooth_mdev
            resmooth_mdev = resmooth_extrapolated + resmooth_mdev
            print(f"Extrapolated points: {extra_s} (smooth), {extra_r} (resmooth)")
            params = ["current1", "current2", "volt1", "volt2", "rpm1", "rpm2"]
            for i, param_name in enumerate(params):
                static = find_static_parameter(config[2], config[1], test_throttle, param=param_name)
                print(param_name, static)
                smooth_param_extrapolated = extrapolate_to_zero(
                    smooth_mdev[extra_s:], known_y_at_zero=static, num_points=15, include_known_zero=True, step=min_mdev[1], x_index=0, y_index=i+2)
                resmoooth_param_extrapolated = extrapolate_to_zero(
                    resmooth_mdev[extra_r:], known_y_at_zero=static, num_points=15, include_known_zero=True, step=0.2, x_index=0, y_index=i+2)
                for j in range(extra_s):
                    smooth_mdev[j].append(smooth_param_extrapolated[j][1])
                for j in range(extra_r):
                    resmooth_mdev[j].append(resmoooth_param_extrapolated[j][1])
            sdev_smooth = stddev_against_reference([row[2:] for row in combined_dtm_list], [x[:2] for x in smooth_mdev], x_index=8, y_index=0)
            sdev_resmooth = stddev_against_reference([row[2:] for row in combined_dtm_list], [x[:2] for x in resmooth_mdev], x_index=8, y_index=0)
            print(f"Smooth sdev: {sdev_smooth}, Resmooth sdev: {sdev_resmooth}")
            print()
            if sdev_smooth > sdev_resmooth:
                final_smoothed_dtm_data = resample(smooth_mdev, step=0.2)
            elif sdev_resmooth >= sdev_smooth:
                final_smoothed_dtm_data = resample(resmooth_mdev, step=0.2)
            final_dtm_dict = {round(v[0], 2): v[1:] for v in final_smoothed_dtm_data}
            final_dtm_list = make_dtm_summary(final_dtm_dict, 25)
            print(tabulate(final_dtm_list, headers=["Airspeed (m/s)", "Thrust (gf)", "Curr1", "Curr2", "Volt1", "Volt2", "RPM1", "RPM2"], tablefmt="fancy_grid"))
            if write_to_files: write_dtm_to_file(final_dtm_list, test_throttle)
            else: print("Skipped: Write DTM results to file.")
            if write_to_files: write_tiny_summary(final_dtm_list, test_throttle)
            else: print("Skipped: Write DTM summary to file.")
            display_graphs(
                [[row[10], row[2]] for row in combined_dtm_list],
                [row[:2] for row in smooth_mdev],
                [row[:2] for row in resmooth_mdev],
                [row[:2] for row in final_dtm_list],
                titles=["Original Data", "Smoothed Data", "ReSmoothed Data", "Final Data"],
                colours=["blue", "green", "red", "black"],
                )
            update_config()
            if is_available:
                s = input("Continue? y/n: ")
                if s in 'Yy':
                    to_continue = True
                    print()
                else:
                    to_continue = False
            else:
                to_continue = False
        
        if not is_available:
            print("All logs processed.")
