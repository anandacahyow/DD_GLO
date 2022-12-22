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

window.geometry("965x710")
#window.resizable(False,False)
window.title("DD GLO Solver")

# ======================================== FRAME ========================================
frame_dragdown = tk.Frame(window, bg='white')
frame_dragdown.grid(row=0,column=0)

frame_dashboard = tk.Frame(window,bg='white')
frame_dashboard.grid(row=1,column=0)

frame_button = tk.Frame(window, bg='white')
frame_button.grid(row=2,column=0,pady=2)
# ======================================== ALGORITHM ========================================

val_Qt = []
Qt = []

cum_qt_ins = []
cum_qt_ins_list = []
cum_qo_ins_list = []

glpc_pred = []
glir_predict = []
glir_input = []

plot_glir = []
plot_qt = []
plot_qo = []

def input_glir():
    global set_glir
    if set_glir.get() != '':
        set_input = int(set_glir.get())
    else:
        set_input = 0
    print('NILAI SETTING GLIR:', set_input)
    
    cond = 'manual'
    return [set_input, cond]

def input_auto():
    cond = 'automatic'
    if input_glir() != 0:
        cond = 'manual'
    return cond

def clear():
    set_glir.delete(0,'end')


def structure():
    global window
    global b
    global i
    global glir_input

    client = ModbusSerialClient(method="rtu", port='COM7', baudrate=9600)
    client.connect()
    
    if i == 0:
        cum_qt = 0
        cum_qo = 0
    else:
        cum_qt = cum_qt_ins_list[-1]
        cum_qo = cum_qo_ins_list[-1]
    period_cond = 10
    # ========================================== INITIALIZATION STATE ==========================================
    if i < 8:
        # ========================================== AGREGATING STATE ==========================================
        t = 0
        #rand_glir = random.uniform(400, 800)
        rand_glir = [410,575,450,430,710,860,870,890]
        #rand_glir.reverse()
        #rand_glir = 854
        
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
            cum_qt_instance = (cum_qt_ins_list[i])/period_cond
        else:
            cum_qt_instance = (cum_qt_ins_list[i]-cum_qt_ins_list[i-1])/period_cond
        
        cum_qt_ins.append(cum_qt_instance)
        glir_input.append(val_GLIR)
        #glpc_pred.append(cum_qt_instance)
    else:
        # ========================================== INDEPENDENT STATE =========s=================================
        val3 = client.read_input_registers(address=191, count=2, unit=113)
        decoded3 = BinaryPayloadDecoder.fromRegisters(val3.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # GLIR
        val_wc = decoded3.decode_32bit_float()
        # ========================================== BUTTONS ==========================================
        cond = 'automatic'
        cond = input_auto()
        if cond == 'manual':
            val_set_glir = input_glir()[0]
            if val_set_glir != 0:
                glir_input[-1] = val_set_glir
        elif cond == 'automatic':
            glir_input = glir_input
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
    
    # ======================================== LABEL FRAME DASHBOARD ========================================
    # ======================================== MEASUREMENTs ========================================
    meas_frame = tk.LabelFrame(frame_dashboard, text="MEASUREMENT")
    meas_frame.grid(row=0,column=0,padx=10,pady=10)

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Treeview",
        background="white",
        foreground="grey",
        fieldbackground="white",)
    style.map('Treeview',background=[('selected','blue')])        

    meas_table = ttk.Treeview(meas_frame, columns=("Variables","Values","Unit"),show='headings',height=8)
    meas_table.column("# 1", width=100,anchor='center')
    meas_table.heading("# 1", text="Variables")
    meas_table.column("# 2", width=150, anchor='center')
    meas_table.heading("# 2", text="Values")
    meas_table.column("# 3", width=100,anchor='center')
    meas_table.heading("# 3", text="Unit")

    qo = (1-val_wc)*cum_qt_ins[-1]
    qw = (val_wc)*val_Qt
    #qw = val_Qt - val_Qo   
    meas_table.tag_configure('odd',background='lightblue')

    #meas_frame.insert

    meas_table.insert('', 'end', text="1", values=('GLIR', str(val_GLIR), 'MCF/day'),tags=('odd'))
    #meas_table.insert('', 'end', text="1", values=('Qt', str(cum_qt_ins[-1]), 'STB/day')) #aggregation needed
    meas_table.insert('', 'end', text="1", values=('Qt', str(val_Qt), 'STB/day')) #aggregation needed
    meas_table.insert('', 'end', text="1", values=('Qt_cum', str(cum_qt), 'bbl'),tags=('odd'))
    meas_table.insert('', 'end', text="1", values=('Qo', str(val_Qo), 'STB/day'))
    meas_table.insert('', 'end', text="1", values=('Qo_cum', str(cum_qo), 'bbl'),tags=('odd'))
    meas_table.insert('', 'end', text="1", values=('wc', str(val_wc), '%'))
    meas_table.insert('', 'end', text="1", values=('Qw', str(qw), 'STB/day'),tags=('odd'))
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
    ax = plot_fig.add_subplot(211)
    ax.set_title('GLIR and Qo FLow Rate')
    ax.plot(time2,plot_glir, label = 'Predicted GLIR', color = 'red')
    ax.set_ylabel('GLIR (MSCFD)')
    ax.grid(True)
    ax1 = plot_fig.add_subplot(212)
    ax1.plot(time2,plot_qo, label='Predicted Qt', color = 'green')
    ax1.set_xlabel('Period')
    ax1.set_ylabel('Qo (STB/day)')
    ax1.grid(True)
    
    canvas = FigureCanvasTkAgg(plot_fig,master=trend_label)
    canvas.draw()
    canvas.get_tk_widget().pack()

    """toolbar = NavigationToolbar2Tk(canvas, trend_label)
    toolbar.update()
    canvas.get_tk_widget().pack()"""
    
    #plot_fig.pause(0.05)
    #plot_fig.clf()"""  

    # ======================================== GLPVs ========================================
    GLPV_frame = tk.LabelFrame(frame_dashboard, text="GAS LIFT VALUE")
    GLPV_frame.grid(row=0,column=1,padx=10,pady=10)

    style = ttk.Style()
    style.theme_use('clam')
    """style.configure("Treeview",
        background="white",
        foreground="grey",
        fieldbackground="white") """              

    GLPV_table = ttk.Treeview(GLPV_frame, columns=("GLIR","Qt"),show='headings', height=8)
    GLPV_table.column("# 1", width=100,anchor='center')
    GLPV_table.heading("# 1", text="GLIR (MCF/day)")
    GLPV_table.column("# 2", width=150,anchor='center')
    GLPV_table.heading("# 2", text="Qt (STB/day)")

    GLPV_table.tag_configure('latest',background='yellow')

    if i == 0:
        GLPV_table.insert('', 'end', text="1", values=(str(glir_input[i]), str(cum_qt_ins[i])),tags=('latest'))
    elif i > 0 and i < 8:
        for l in range(0,i+1):
            if l != i:
                GLPV_table.insert('', 'end', text="1", values=(str(glir_input[l]), str(cum_qt_ins[l])))
            else:
                GLPV_table.insert('', 'end', text="1", values=(str(glir_input[l]), str(cum_qt_ins[l])),tags=('latest'))
    else:
        for k in range(i-7,i):
            if k < i-1:
                GLPV_table.insert('', 'end', text="1", values=(str(glir_input[k]), str(cum_qt_ins[k])))
            else:
                GLPV_table.insert('', 'end', text="1", values=(str(glir_input[k]), str(cum_qt_ins[k])), tags=('latest'))

    GLPV_table.pack()

    # ======================================== GLPCs ========================================
    GLPC_frame = tk.LabelFrame(frame_dashboard, text="GAS LIFT PERFORMANCE CURVE")
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
    #print(f"X REG: {x_reg}\n Y REG: {y_reg}")

    mymodel = np.poly1d(np.polyfit(x_reg, y_reg, 2))
    myline = np.linspace(min(x_reg), max(x_reg), len(x_reg))
    
    plot_fig2 = Figure(figsize=(3,3))
    ax2 = plot_fig2.add_subplot(111)
    ax2.set_title('GLPC Curve')
    ax2.plot(myline, mymodel(myline), color="orange")
    ax2.scatter(x_reg,y_reg)
    ax2.set_xlabel('GLIR (MSCFD)')
    ax2.set_ylabel('Qt (STB/day)')
    ax2.grid(True)
    
    canvas2 = FigureCanvasTkAgg(plot_fig2,master=GLPC_label)
    canvas2.draw()
    canvas2.get_tk_widget().pack()

    """toolbar2 = NavigationToolbar2Tk(canvas2, GLPC_label)
    toolbar2.update()
    canvas2.get_tk_widget().pack()"""

    window.after(2000, structure)
    b+=1
    i+=1

b = 0
i = 0
img = ImageTk.PhotoImage(Image.open("header.png"))
window.after(2000,structure)

dragdown_label = tk.Label(frame_dragdown,image = img)
dragdown_label.pack()

# ======================================== BUTTON FRAME ========================================
# ======================================== GLPCs ========================================
button_label = tk.LabelFrame(frame_button, text="ACTIONS COMMANDS")
button_label.grid(row=0,column=0,padx=10,pady=10)

set_glir = tk.Entry(button_label)
set_glir.grid(row=0,column=0,padx=10)

setting_button = tk.Button(button_label, text="SET GLIR", command=input_glir)
setting_button.grid(row=0,column=1,padx=10)

automatic_button = tk.Button(button_label, text="AUTOMATIC", command=clear)
automatic_button.grid(row=0,column=2,padx=10)

#auto_button = tk.Button(button_label, text="MODE : AUTOMATIC",command=input_auto)
#auto_button.grid(row=0,column=3,padx=10)

# ======================================== MAIN LOOP GUI ========================================
window.mainloop()