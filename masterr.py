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


def main():
    client = ModbusSerialClient(method="rtu", port='COM7', baudrate=9600)
    client.connect()
    
    val_Qt = []
    Qt = []
    cum_qt = 0
    cum_qt_ins = []
    cum_qt_ins_list = []
    glir_input = []
    i = 0

    plot_glir = []
    plot_qt = []
    period_cond = 15
    while 1:
        # ========================================== INITIALIZATION STATE ==========================================
        if i < 8:
            # ========================================== AGREGATING STATE ==========================================
            t = 0
            rand_glir = random.uniform(0, 1000)
            rand_glir = [410,575,450,430,710,860,870,890]
            val2 = client.write_register(7031, int(rand_glir[i]), unit=114)  #GLIR_opt
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
            
            #val4 = client.read_input_registers(address=111, count=2, unit=113)
            #decoded4 = BinaryPayloadDecoder.fromRegisters(val4.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # GLIR
            #val_cum = decoded4.decode_32bit_float()
            cum_qt_ins_list.append(cum_qt)
            if i == 0:
                cum_qt_instance = (cum_qt_ins_list[i])/period_cond
            else:
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
        time2 = np.arange(0,len(plot_glir),1)
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
        plt.clf()

        i += 1

        sleep(1)
    client.close()


if __name__ == "__main__":
    main()
