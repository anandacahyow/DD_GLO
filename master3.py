import argparse
import logging
from datetime import datetime
from time import sleep

import matplotlib.pyplot as plt
import numpy as np

from pymodbus.client.sync import ModbusSerialClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

logging.basicConfig(level=logging.INFO)


def main():
    client = ModbusSerialClient(method="rtu", port='COM7', baudrate=9600)
    client.connect()
    
    val_Qt = []
    Qt = []
    i = 0
    while 1:
        # ========================== INPUT REGISTERS (VX) ===============================
        val1 = client.read_input_registers(address=167, count=2, unit=113)
        #val1 = client.read_input_registers(address=167, count=2, unit=113)
        decoded1 = BinaryPayloadDecoder.fromRegisters(val1.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # GLIR
        val_Qt = decoded1.decode_32bit_float()

        # ========================== LOGGING INPUT REGISTER (VX) ===============================
        logging.info("{} Qt: {}".format(datetime.now(), val_Qt))        
        #Qt.append(val_Qt)

        # ========================== HOLDING REGISTERS (ABB) ===============================
        glir_pred = int(i + val_Qt)
        val2 = client.write_register(7036, glir_pred, unit=114)  #GLIR_opt
        val2 = client.read_holding_registers(7036, 1, unit=114)
        #decoded2 = BinaryPayloadDecoder.fromRegisters(val2.registers, byteorder=Endian.Big, wordorder=Endian.Little)  # GLIR
        val_GLIR = val2.registers[0]
        
        # ========================== LOGGING HOLDING REGISTER (ABB) ===============================
        logging.info(f"{datetime.now()} GLIR : {val_GLIR}")

        i += 1

        sleep(1)
    client.close()


if __name__ == "__main__":
    main()
