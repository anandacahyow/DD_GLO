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
    
    #i = -7 #alternatif
    i = 0
    num = 8
    val_GLIR = [0]
    val_GLIR_data = [0]
    qt_data = [0]
    val_Qt = [0]

    Qo = []
    GLIR = []
    Qt = []
    wc = []

    GLIR_predict = []
    Qt_predict = []

    day = 8

    plt.ion()
    while 1:
        print("==================================================================")
        print(i)
        #num = 8
        #val = DDGLO("well_VX2_calc.csv",i,'Qt')
        #vall = DDGLO("well_VX2_calc.csv",i,'GLIR')
        #GLIR_opt = val.RegOpt(i)[4]
        #GLIR_data = vall.DataRef('GLIR')
        #Qt_opt = val.RegOpt(i)[5]
        
        # ========================== INPUT REGISTERS (VX) ===============================
        val1 = client.read_input_registers(address=109, count=2, unit=113)  # qo_lc
        val2 = client.read_input_registers(address=2024, count=2, unit=113)  # qt_lc
        val3 = client.read_input_registers(address=191, count=2, unit=113)  # wc
        val4 = client.read_holding_registers(2022, 2, unit=113) # GLIR

        decoded1 = BinaryPayloadDecoder.fromRegisters(val1.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # qo_lc
        decoded2 = BinaryPayloadDecoder.fromRegisters(val2.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # qt_lc
        decoded3 = BinaryPayloadDecoder.fromRegisters(val3.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # wc
        decoded4 = BinaryPayloadDecoder.fromRegisters(val4.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # GLIR

        val_Qo = decoded1.decode_32bit_float()
        val_Qt = decoded2.decode_32bit_float()
        val_wc = decoded3.decode_32bit_float()
        val_GLIR = decoded4.decode_32bit_float()
        
        # ========================== LOGGING INPUT REGISTER (VX) ===============================
        logging.info("{} Qo: {}".format(datetime.now(), val_Qo))
        logging.info("{} Qt: {}".format(datetime.now(), val_Qt))
        logging.info("{} Wc: {}".format(datetime.now(), val_wc))
        logging.info("{} GLIR: {}".format(datetime.now(), val_GLIR))
        #logging.info(f"{datetime.now()} GLIR: {val4.registers[0]}")

        Qo.append(val_Qo)
        Qt.append(val_Qt)
        wc.append(val_wc)
        GLIR.append(val_GLIR)
        #print(f"NILAI READ DATA: {Qo} || {Qt} || {wc} || {GLIR}")

        if len(Qo) <= day-1:
            logging.error("REGRESSION DATA IS NOT SUFFICIENT")
            #print("data not sufficient")
        else:
            regoptim = DDGLO(GLIR, Qt, wc, i-7)
            glir_pred = regoptim.RegOpt()[0]
            qt_pred = regoptim.RegOpt()[1]

            val5 = client.write_register(7001, glir_pred, unit=114)  #GLIR_opt
            val5 = client.read_holding_registers(7001, 10, unit=114)  # GLIR
            
            Qt_predict.append(qt_pred)
            GLIR_predict.append(glir_pred)
        
            logging.info(f"{datetime.now()} GLIR SETPOINT: {val5.registers[0]}")
        
        #logging.info("{} GLIR Pred: {}".format(datetime.now(), len(GLIR_predict)))  
        #logging.info("{} Qt Pred: {}".format(datetime.now(), len(Qt_predict)))

        #logging.info("{} GLIR: {}".format(datetime.now(), len(GLIR[7:])))
        #logging.info("{} Qt: {}".format(datetime.now(), len(Qt[7:])))
        
        # ========================== HOLDING REGISTERS (ABB) ===============================
        #val5 = client.write_register(7001, GLIR_opt, unit=114)  #GLIR_opt
        
        #val_GLIR.append(GLIR_opt)
        #val_GLIR_data.append(GLIR_data)
        #val_Qt.append(Qt_opt)

        # ========================== LOGGING HOLDING REGISTER (ABB) ===============================
        #logging.info(f"{datetime.now()} GLIR OPT: {val5.registers[0]} || {np.shape(val_GLIR)}")

        # ========================== WELL SYSTEM DYNAMICS ===============================
        """well = WellDyn(val_Qt,i,'well_VX2_calc.csv')
        y_sys = well.WellSys(val_Qt,i,'well_VX2_calc.csv')

        qt = val.DataRef('Qt')
        qt_data.append(qt)"""

        # ========================== REAL-TIME PLOTTING ===============================
        
        """t = np.arange(0,i+1,1)
        t1 = np.arange(0,i+2,1)
        
        if len(y_sys) < 4:
            tt = np.arange(0,3,1)
        #if len(y_sys) == 4:
        #    tt = np.arange(0,4,1)
        else:
            tt = np.arange(0,i+2,1)"""
        
        #logging.info(f"NILAI y_sys: {y_sys}")
        #logging.info(f"NILAI tt: {tt}")
        #logging.info(f"NILAI len y_sys: {len(y_sys)}")
        
        if len(Qo) <= day-1:
            print("\n")
        else:
            # ========================== R2 VALUE of QT PREDICTION (REGRESSION BASED) ===============================
            R = np.corrcoef(Qt_predict, Qt[7:], rowvar=False)[0, 1] # R2 Qt
            R = np.corrcoef(GLIR_predict, GLIR[7:], rowvar=False)[0, 1] # R2 GLIR
            R2 = R**2

            #r2_total.append(R2)
            logging.info("{}-th Day || GLIR R2 VALUE : {}".format(i-7,R2))

            """t = np.arange(0,i-6,1)
            #t1 = np.arange(0,i-5,1)
            #print(f"LENGTH T: {len(t)} nilainya: {t}")
            plt.figure(1)
            plt.plot(t,GLIR_predict, label = 'Predicted GLIR', color = 'red')
            plt.plot(t,Qt_predict, label='Predicted Qt', color = 'green')
            #plt.plot(t1,GLIR[6:], label='GLIR DATA', alpha = 0.4, linewidth = 3, color = 'blue')
            plt.plot(t,GLIR[6:], label='GLIR DATA', alpha = 0.4, linewidth = 3, color = 'blue')
            plt.plot(t,Qt[7:], label='Qt Data', color = 'orange')
        
            plt.title("Historical Data and Prediction Comparison of Qt and GLIR\nnote: Qt Prediction based on Regression")
            plt.xlabel(f"Day {i-7}-th")
            plt.ylabel('GLIR (mscfd) & Qt (bopd)')
            plt.legend()
            plt.grid()
            plt.pause(0.05)
            plt.clf()"""

            #GLIR.remove(0)

        sleep(1)
        i += 1
    client.close()


if __name__ == "__main__":
    main()
