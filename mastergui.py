import tkinter as tk
from tkinter import ttk #widget
from threading import Thread
from time import sleep
from PIL import ImageTk, Image

import argparse
import logging
from datetime import datetime
from time import sleep

from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import random

from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,NavigationToolbar2Tk)

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
cum_qo_ins_list = []
glpc_pred = []
glir_predict = []
glir_input = []
#i = 0

plot_glir = []
plot_qt = []
plot_qo = []

def structure():
    global window
    global b
    global i
    print(i)

    client = ModbusSerialClient(method="rtu", port='COM7', baudrate=9600)
    client.connect()
    
    if i == 0:
        cum_qt = 0
        cum_qo = 0
    else:
        cum_qt = cum_qt_ins_list[-1]
        cum_qo = cum_qo_ins_list[-1]
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
            decoded1 = BinaryPayloadDecoder.fromRegisters(val1.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # Qt
            val_Qt = decoded1.decode_32bit_float()
            
            val4 = client.read_input_registers(address=165, count=2, unit=113)
            decoded4 = BinaryPayloadDecoder.fromRegisters(val4.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # Qt
            val_Qo = decoded4.decode_32bit_float()

            cum_qt += val_Qt
            cum_qo += val_Qo
            logging.info(f"[{i}] {datetime.now()} Qt rate : {val_Qt}")
            
            plot_glir.append(val_GLIR)    
            plot_qt.append(val_Qt)
            plot_qo.append(val_Qo)
            #sleep(1) #sampling period same with slave
            t += 1
 
        cum_qt_ins_list.append(cum_qt)
        cum_qo_ins_list.append(cum_qo)
        
        if i == 0:
            print(f"VAL CUM QT INS: {cum_qt_ins_list}")
            cum_qt_instance = (cum_qt_ins_list[i])/period_cond
        else:
            print(f"VAL CUM QT INS: {cum_qt_ins_list}")
            cum_qt_instance = (cum_qt_ins_list[i]-cum_qt_ins_list[i-1])/period_cond
        
        cum_qt_ins.append(cum_qt_instance)
        glir_input.append(val_GLIR)
        #glpc_pred.append(cum_qt_instance)
        
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
        x_pred = regoptim.RegOpt()[2]
        y_pred = regoptim.RegOpt()[3]
        # ========================================== AGREGATING STATE ==========================================
        t = 0
        val2 = client.write_register(7031, int(glir_pred), unit=114)  #GLIR_opt
        val2 = client.read_holding_registers(7031, 1, unit=114) #GLIR_opt
        val_GLIR = val2.registers[0]
        logging.info(f"[{i}] {datetime.now()} GLIR : {val_GLIR}")
        

        while t < period_cond: # Periods of Sampling Time Condition 1              
            val1 = client.read_input_registers(address=167, count=2, unit=113)
            decoded1 = BinaryPayloadDecoder.fromRegisters(val1.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # Qt
            val_Qt = decoded1.decode_32bit_float()
            
            val4 = client.read_input_registers(address=165, count=2, unit=113)
            decoded4 = BinaryPayloadDecoder.fromRegisters(val4.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # Qt
            val_Qo = decoded4.decode_32bit_float()

            cum_qt += val_Qt
            cum_qo += val_Qo
            logging.info(f"[{i}] {datetime.now()} Qt rate : {val_Qt}")
            
            plot_glir.append(val_GLIR)    
            plot_qt.append(val_Qt)
            plot_qo.append(val_Qo)
            #sleep(1) #sampling period same with slave
            t += 1

        cum_qt_ins_list.append(cum_qt)
        cum_qo_ins_list.append(cum_qo)
        if i == 0:
            cum_qt_instance = (cum_qt_ins_list[i])/period_cond
        else:
            cum_qt_instance = (cum_qt_ins_list[i]-cum_qt_ins_list[i-1])/period_cond
        
        cum_qt_ins.append(cum_qt_instance)
        glir_input.append(val_GLIR)
        #glpc_pred.append(y_pred)
        #glir_predict.append(x_pred)
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
    style.theme_use('default')
    style.configure("Treeview",
        background="white",
        foreground="grey",
        fieldbackground="white")

    meas_table = ttk.Treeview(meas_frame, columns=("Variables","Values","Unit"),show='headings')
    meas_table.column("# 1", width=100,anchor='center')
    meas_table.heading("# 1", text="Variables")
    meas_table.column("# 2", width=150, anchor='center')
    meas_table.heading("# 2", text="Values")
    meas_table.column("# 3", width=100,anchor='center')
    meas_table.heading("# 3", text="Unit")

    qo = (1-val_wc)*cum_qt_ins[-1]
    qw = (val_wc)*val_Qt
    meas_table.tag_configure('odd',background="yellow")
    meas_table.insert('', 'end', text="1", values=('GLIR', str(val_GLIR), 'MCF/day'),tags=('odd',))
    #meas_table.insert('', 'end', text="1", values=('Qt', str(cum_qt_ins[-1]), 'STB/day')) #aggregation needed
    meas_table.insert('', 'end', text="1", values=('Qt', str(val_Qt), 'STB/day')) #aggregation needed
    meas_table.insert('', 'end', text="1", values=('Qt_cum', str(cum_qt), 'bbl'))
    meas_table.insert('', 'end', text="1", values=('Qo', str(val_Qo), 'STB/day'))
    meas_table.insert('', 'end', text="1", values=('Qo_cum', str(cum_qo), 'bbl'))
    meas_table.insert('', 'end', text="1", values=('wc', str(val_wc), '%'))
    meas_table.insert('', 'end', text="1", values=('Qw', str(qw), 'STB/day'))
    meas_table.pack()
    # ======================================== TRENDs ========================================
    trend_frame = tk.LabelFrame(frame_dashboard, text="TRENDS")
    trend_frame.grid(row=1,column=0,padx=10,pady=10)

    trend_label = tk.LabelFrame(trend_frame)
    trend_label.pack()

    # ========================================== VISUALIZATION ==========================================
    #print(f"LENGTH plot_glir {len(plot_glir)}")
    time2 = np.arange(0,len(plot_glir),1)

    plot_fig = Figure(figsize=(5,3))
    plot_fig.add_subplot(211).plot(time2,plot_glir, label = 'Predicted GLIR', color = 'red')
    plot_fig.add_subplot(212).plot(time2,plot_qo, label='Predicted Qt', color = 'green')
    
    canvas = FigureCanvasTkAgg(plot_fig,master=trend_label)
    canvas.draw()
    canvas.get_tk_widget().pack()

    toolbar = NavigationToolbar2Tk(canvas, trend_label)
    toolbar.update()
    canvas.get_tk_widget().pack()
    
    #plot_fig.pause(0.05)
    #plot_fig.clf()"""  

    # ======================================== GLPVs ========================================
    GLPV_frame = tk.LabelFrame(frame_dashboard, text="GAS LIFT VALUE")
    GLPV_frame.grid(row=0,column=1,padx=10,pady=10)

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Treeview",
        background="white",
        foreground="grey",
        fieldbackground="white")               

    GLPV_table = ttk.Treeview(GLPV_frame, columns=("GLIR","Qt"),show='headings')
    GLPV_table.column("# 1", width=100,anchor='center')
    GLPV_table.heading("# 1", text="GLIR (MCF/day)")
    GLPV_table.column("# 2", width=150,anchor='center')
    GLPV_table.heading("# 2", text="Qt (STB/day)")

    GLPV_table.tag_configure('latest',background="yellow")

    if i == 0:
        GLPV_table.insert('', 'end', text="1", values=(str(glir_input[i]), str(cum_qt_ins[i])),tags=('latest',))
    elif i > 0 and i < 8:
        for l in range(0,i+1):
            if l == i+1:
                GLPV_table.insert('', 'end', text="1", values=(str(glir_input[l]), str(cum_qt_ins[l])), tags=('latest',))
            else:
                GLPV_table.insert('', 'end', text="1", values=(str(glir_input[l]), str(cum_qt_ins[l])), tags=('latest',))
    else:
        for k in range(i-7,i):
            if k == i:
                GLPV_table.insert('', 'end', text="1", values=(str(glir_input[k]), str(cum_qt_ins[k])), tags=('latest',))
            else:
                GLPV_table.insert('', 'end', text="1", values=(str(glir_input[k]), str(cum_qt_ins[k])))

    GLPV_table.pack()

    # ======================================== GLPCs ========================================
    GLPC_frame = tk.LabelFrame(frame_dashboard, text="GAS LIFT CURVE")
    GLPC_frame.grid(row=1,column=1,padx=10,pady=10)

    GLPC_label = tk.LabelFrame(GLPC_frame)
    GLPC_label.pack()

    # ========================================== VISUALIZATION ==========================================
    if i < 8:
        x_reg = glir_input[0:i+1]
        y_reg = cum_qt_ins[0:i+1]
        x_reg.sort()
        y_reg.sort()
        x_reg = np.insert(x_reg, 0, 0)
        y_reg = np.insert(y_reg, 0, 0)
    else:
        x_reg = x_pred
        y_reg = y_pred
    print(f"X REG: {x_reg}\n Y REG: {y_reg}")

    mymodel = np.poly1d(np.polyfit(x_reg, y_reg, 2))
    myline = np.linspace(min(x_reg), max(x_reg), len(x_reg))
    
    plot_fig2 = Figure(figsize=(5,3))
    plot_fig2.add_subplot(111).plot(myline, mymodel(myline), color="orange")
    
    canvas2 = FigureCanvasTkAgg(plot_fig2,master=GLPC_label)
    canvas2.draw()
    canvas2.get_tk_widget().pack()

    toolbar2 = NavigationToolbar2Tk(canvas2, GLPC_label)
    toolbar2.update()
    canvas2.get_tk_widget().pack()

    window.after(1000, structure)
    b+=1
    i+=1

# ======================================== MAIN LOOP GUI ========================================
b = 0
i = 0
window.after(1000,structure)

window.mainloop()