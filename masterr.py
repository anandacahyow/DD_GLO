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
    while 1:

        if i < 8:
            t = 0
            period_cond = 10
            rand_glir = random.uniform(500, 800)
            val2 = client.write_register(7036, int(rand_glir), unit=114)  #GLIR_opt
            val2 = client.read_holding_registers(7036, 1, unit=114) #GLIR_opt
            val_GLIR = val2.registers[0]
            logging.info(f"[{i}] {datetime.now()} GLIR : {val_GLIR}")
            
            while t < period_cond: # Periods of Sampling Time Condition 1                
                val1 = client.read_input_registers(address=167, count=2, unit=113)
                decoded1 = BinaryPayloadDecoder.fromRegisters(val1.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # GLIR
                val_Qt = decoded1.decode_32bit_float()
                
                cum_qt += val_Qt
                logging.info(f"[{i}] {datetime.now()} Qt rate : {val_Qt}")
                sleep(1) #sampling period same with slave
                t += 1
            
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
            #input DD GLO
            print(f"{i} GLIR Instance: {glir_input}")
            print(f"{i} INSTANCE from Cumulative: {cum_qt_ins}")
            #print('done')

        i += 1

        sleep(1)
    client.close()


if __name__ == "__main__":
    main()
