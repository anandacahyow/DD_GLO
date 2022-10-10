import argparse
import logging
from datetime import datetime
from time import sleep

import matplotlib.pyplot as plt
import numpy as np

from pymodbus.client.sync import ModbusSerialClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

from DDGLO import DDGLO
from DDGLO import WellDyn

logging.basicConfig(level=logging.INFO)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-po", "--port", help="serial port to use", dest="port")
    args = parser.parse_args()
    client = ModbusSerialClient(method="rtu", port=args.port, baudrate=9600)
    client.connect()
    i = 0
    num = 8
    val_GLIR = [0]
    val_GLIR_data = [0]
    qt_data = [0]
    val_Qt = [0]
    plt.ion()
    while 1:
        num = 8
        val = DDGLO("well_VX2_calc.csv",i,'Qt')
        vall = DDGLO("well_VX2_calc.csv",i,'GLIR')
        GLIR_opt = val.RegOpt(i)[4]
        GLIR_data = vall.DataRef('GLIR')

        Qt_opt = val.RegOpt(i)[5]
        # ========================== INPUT REGISTERS (VX) ===============================
        val1 = client.read_input_registers(address=109, count=2, unit=113)  # qo_lc
        val2 = client.read_input_registers(address=2024, count=2, unit=113)  # qt_lc
        val3 = client.read_input_registers(address=191, count=2, unit=113)  # wc
        # val4 = client.read_input_registers(address=999, count=3, unit=113)  
        val4 = client.read_holding_registers(2022, 2, unit=113) # GLIR

        decoded1 = BinaryPayloadDecoder.fromRegisters(val1.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # qo_lc
        decoded2 = BinaryPayloadDecoder.fromRegisters(val2.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # qt_lc
        decoded3 = BinaryPayloadDecoder.fromRegisters(val3.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # wc
        decoded4 = BinaryPayloadDecoder.fromRegisters(val4.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # GLIR

        # ========================== LOGGING INPUT REGISTER (VX) ===============================
        logging.info("{} Qo: {}".format(datetime.now(), decoded1.decode_32bit_float()))
        logging.info("{} Qt: {}".format(datetime.now(), decoded2.decode_32bit_float()))
        logging.info("{} Wc: {}".format(datetime.now(), decoded3.decode_32bit_float()))
        logging.info("{} GLIR: {}".format(datetime.now(), decoded4.decode_32bit_float()))
        #logging.info(f"{datetime.now()} GLIR: {val4.registers[0]}")

        # ========================== HOLDING REGISTERS (ABB) ===============================
        val5 = client.write_register(7001, GLIR_opt, unit=114)  #GLIR_opt
        val5 = client.read_holding_registers(7001, 10, unit=114)  # GLIR
        val_GLIR.append(GLIR_opt)
        val_GLIR_data.append(GLIR_data)

        val_Qt.append(Qt_opt)

        # ========================== LOGGING HOLDING REGISTER (ABB) ===============================
        #logging.info(f"{datetime.now()} GLIR: {val5.registers[0]}")
        logging.info(f"{datetime.now()} GLIR OPT: {val5.registers[0]} || {np.shape(val_GLIR)}")

        # ========================== WELL SYSTEM DYNAMICS ===============================
        well = WellDyn(val_Qt,i,'well_VX2_calc.csv')
        y_sys = well.WellSys(val_Qt,i,'well_VX2_calc.csv')

        qt = val.DataRef('Qt')
        qt_data.append(qt)
        # ========================== REAL-TIME PLOTTING ===============================
        
        t = np.arange(0,i+1,1)
        t1 = np.arange(0,i+2,1)
        
        if len(y_sys) < 4:
            tt = np.arange(0,3,1)
        #if len(y_sys) == 4:
        #    tt = np.arange(0,4,1)
        else:
            tt = np.arange(0,i+2,1)
        
        #logging.info(f"NILAI y_sys: {y_sys}")
        #logging.info(f"NILAI y_sys: {y_sys}")
        #logging.info(f"NILAI tt: {tt}")
        #logging.info(f"NILAI len y_sys: {len(y_sys)}")

        plt.plot(t1,qt_data, label = 'Qt Data')
        plt.plot(t1,val_GLIR, label='GLIR OPT')
        plt.plot(t1,val_Qt, label='QT PRED DATA')
        plt.plot(t1,val_GLIR_data, label='GLIR Data')
        plt.plot(tt,y_sys, label='Qt Pred')
        
        plt.title("Historical Data and Prediction Comparison of Qt and GLIR")
        plt.xlabel(f"Day {i}-th")
        plt.ylabel('GLIR (mscfd)')
        plt.legend()
        plt.grid()
        plt.pause(0.05)
        plt.clf()

        sleep(1)
        i += 1
    client.close()


if __name__ == "__main__":
    main()
