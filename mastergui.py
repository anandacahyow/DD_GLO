import tkinter as tk
from tkinter import ttk #widget
from threading import Thread
from time import sleep
from PIL import ImageTk, Image

import argparse
import logging
from datetime import datetime
from time import sleep

import matplotlib.pyplot as plt
import numpy as np
import random

from pymodbus.client.sync import ModbusSerialClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

from DDGLO import DDGLO

logging.basicConfig(level=logging.INFO)

# ======================================== INITIAL ========================================
window = tk.Tk()
window.configure(bg="white")
window.geometry("900x600")
#window.resizable(False,False)
window.title("DD GLO Solver")

val_Qt = []
Qt = []

cum_qt_ins = []
cum_qt_ins_list = []
glir_input = []
#i = 0

plot_glir = []
plot_qt = []

def structure():
    global window
    global b
    global i
    print(i)

    client = ModbusSerialClient(method="rtu", port='COM7', baudrate=9600)
    client.connect()
    
    if i == 0:
        cum_qt = 0
    else:
        cum_qt = cum_qt_ins_list[-1]
    period_cond = 15
    # ========================================== INITIALIZATION STATE ==========================================
    if i < 8:
        # ========================================== AGREGATING STATE ==========================================
        t = 0
        rand_glir = random.uniform(0, 1000)
        rand_glir = [410,575,450,430,710,860,870,890]
        
        val2 = client.write_register(7031, int(rand_glir[i]), unit=114)  #GLIR_opt
        val2 = client.read_holding_registers(7031, 1, unit=114) #GLIR_opt
        val_GLIR = val2.registers[0]
        
        val3 = client.read_input_registers(address=191, count=2, unit=113)
        decoded3 = BinaryPayloadDecoder.fromRegisters(val3.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # GLIR
        val_wc = decoded3.decode_32bit_float()
        
        logging.info(f"[{i}] {datetime.now()} GLIR : {val_GLIR}")
        
        while t < period_cond: # Periods of Sampling Time Condition 1            
            val1 = client.read_input_registers(address=167, count=2, unit=113)
            decoded1 = BinaryPayloadDecoder.fromRegisters(val1.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # GLIR
            val_Qt = decoded1.decode_32bit_float()
            
            cum_qt += val_Qt
            logging.info(f"[{i}] {datetime.now()} Qt rate : {val_Qt}")
            
            plot_glir.append(val_GLIR)    
            plot_qt.append(val_Qt)
            #sleep(1) #sampling period same with slave
            t += 1
 
        cum_qt_ins_list.append(cum_qt)
        if i == 0:
            print(f"VAL CUM QT INS: {cum_qt_ins_list}")
            cum_qt_instance = (cum_qt_ins_list[i])/period_cond
        else:
            print(f"VAL CUM QT INS: {cum_qt_ins_list}")
            cum_qt_instance = (cum_qt_ins_list[i]-cum_qt_ins_list[i-1])/period_cond
        
        cum_qt_ins.append(cum_qt_instance)
        glir_input.append(val_GLIR)
        
        print(f"{i} GLIR Instance: {glir_input}")
        print(f"{i} INSTANCE from Cumulative: {cum_qt_ins}")
    else:
        # ========================================== INDEPENDENT STATE ==========================================
        val3 = client.read_input_registers(address=191, count=2, unit=113)
        decoded3 = BinaryPayloadDecoder.fromRegisters(val3.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # GLIR
        val_wc = decoded3.decode_32bit_float()
        # ========================================== SOLVER ==========================================
        regoptim = DDGLO(glir_input, cum_qt_ins, val_wc, i-7)
        glir_pred = regoptim.RegOpt()[0]
        qt_pred = regoptim.RegOpt()[1]
        # ========================================== AGREGATING STATE ==========================================
        t = 0
        val2 = client.write_register(7031, int(glir_pred), unit=114)  #GLIR_opt
        val2 = client.read_holding_registers(7031, 1, unit=114) #GLIR_opt
        val_GLIR = val2.registers[0]
        logging.info(f"[{i}] {datetime.now()} GLIR : {val_GLIR}")
        
        while t < period_cond: # Periods of Sampling Time Condition 1              
            val1 = client.read_input_registers(address=167, count=2, unit=113)
            decoded1 = BinaryPayloadDecoder.fromRegisters(val1.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # GLIR
            val_Qt = decoded1.decode_32bit_float()
            
            cum_qt += val_Qt
            logging.info(f"[{i}] {datetime.now()} Qt rate : {val_Qt}")

            plot_glir.append(val_GLIR)    
            plot_qt.append(val_Qt)
            #sleep(1) #sampling period same with slave
            t += 1

        cum_qt_ins_list.append(cum_qt)
        if i == 0:
            cum_qt_instance = (cum_qt_ins_list[i])/period_cond
        else:
            cum_qt_instance = (cum_qt_ins_list[i]-cum_qt_ins_list[i-1])/period_cond
        
        cum_qt_ins.append(cum_qt_instance)
        glir_input.append(val_GLIR)

    # ========================================== VISUALIZATION ==========================================
    #print(f"LENGTH plot_glir {len(plot_glir)}")
    """time2 = np.arange(0,len(plot_glir),1)
    time = np.arange(0,i+1,1)
    plt.figure(1)
    plt.plot(time2,plot_glir, label = 'Predicted GLIR', color = 'red')
    plt.plot(time2,plot_qt, label='Predicted Qt', color = 'green')
    
    plt.title("Historical Data and Prediction Comparison of Qt and GLIR\nnote: Qt Prediction based on 3rd Order Transfer Function")
    plt.xlabel(f"Day {i-7}-th")
    plt.ylabel('GLIR (mscfd) & Qt (bopd)')
    plt.legend()
    plt.grid()
    plt.pause(0.05)
    plt.clf()"""

    #i += 1

    #sleep(1)
    client.close()
    # ======================================== FRAME ========================================
    frame_dragdown = tk.Frame(window)
    #frame_dragdown.grid(row=0,column=0,padx=5,pady=5,ipadx=75,ipady=590)
    frame_dragdown.grid(row=0,column=0,padx=5,pady=5)
    #frame_dragdown.pack(padx=5,pady=5,ipadx=200,ipady=590)

    frame_dashboard = tk.Frame(window)
    frame_dashboard.grid(row=0,column=1,padx=5,pady=5,ipadx=850,ipady=590)
    #frame_dashboard.pack(padx=210,pady=5,ipadx=685,ipady=590)

    # ======================================== LABEL FRAME DRAGDOWN ========================================
    #logo_label = tk.LabelFrame(frame_dragdown)
    #logo_label.pack()
    img = ImageTk.PhotoImage(Image.open("foto.png"))
    dragdown_label = tk.Label(frame_dragdown,image = img)
    dragdown_label.pack()
    # ======================================== LABEL FRAME DASHBOARD ========================================
    # ======================================== MEASUREMENTs ========================================
    meas_frame = tk.LabelFrame(frame_dashboard, text="MEASUREMENT")
    meas_frame.grid(row=0,column=0,padx=10,pady=10)

    style = ttk.Style()
    style.theme_use('clam')

    meas_table = ttk.Treeview(meas_frame, columns=("Variables","Values","Unit"),show='headings')
    meas_table.column("# 1", anchor='center')
    meas_table.heading("# 1", text="Variables")
    meas_table.column("# 2", anchor='center')
    meas_table.heading("# 2", text="Values")
    meas_table.column("# 3", anchor='center')
    meas_table.heading("# 3", text="Unit")

    qo = (1-val_wc)*cum_qt_ins[-1]
    meas_table.insert('', 'end', text="1", values=('GLIR', str(val_GLIR), 'MCF/day'))
    meas_table.insert('', 'end', text="1", values=('Qt', str(cum_qt_ins[-1]), 'STB/day'))
    meas_table.insert('', 'end', text="1", values=('Qt_cum', str(cum_qt), 'bbl'))
    meas_table.insert('', 'end', text="1", values=('Qo', str(qo), 'STB/day'))
    meas_table.insert('', 'end', text="1", values=('wc', str(val_wc), '%'))
    meas_table.pack()
    # ======================================== TRENDs ========================================
    trend_frame = tk.LabelFrame(frame_dashboard, text="TRENDS")
    trend_frame.grid(row=1,column=0,padx=10,pady=10)

    trend_label = tk.Label(trend_frame, text="TRENDS")
    trend_label.grid(row=0,column=0)

    # ======================================== GLPVs ========================================
    GLPV_frame = tk.LabelFrame(frame_dashboard, text="GAS LIFT VALUE")
    GLPV_frame.grid(row=0,column=1,padx=10,pady=10)

    style = ttk.Style()
    style.theme_use('clam')

    GLPV_table = ttk.Treeview(GLPV_frame, columns=("GLIR","Qt"),show='headings')
    GLPV_table.column("# 1", anchor='center')
    GLPV_table.heading("# 1", text="GLIR (MCF/day)")
    GLPV_table.column("# 2", anchor='center')
    GLPV_table.heading("# 2", text="Qt (STB/day)")

    
    if i == 0:
        GLPV_table.insert('', 'end', text="1", values=(str(glir_input[i]), str(cum_qt_ins[i])))
    elif i > 0 and i < 8:
        print(i)
        for l in range(0,i+1):
            GLPV_table.insert('', 'end', text="1", values=(str(glir_input[l]), str(cum_qt_ins[l])))
    else:
        for k in range(i-7,i):
            GLPV_table.insert('', 'end', text="1", values=(str(glir_input[k]), str(cum_qt_ins[k])))

    GLPV_table.pack()

    # ======================================== GLPCs ========================================
    GLPC_frame = tk.LabelFrame(frame_dashboard, text="GAS LIFT CURVE")
    GLPC_frame.grid(row=1,column=1,padx=10,pady=10)

    GLPC_label = tk.Label(GLPC_frame, text="GAS LIFT CURVE")
    GLPC_label.grid(row=0,column=0)
    window.after(1000, structure)
    b+=1
    i+=1

# ======================================== MAIN LOOP GUI ========================================
b = 0
i = 0
window.after(1000,structure)

window.mainloop()