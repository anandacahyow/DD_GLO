import argparse
import csv
from datetime import datetime
import logging
from math import nan
import threading
import pandas

from time import sleep
from pymodbus.server.sync import StartSerialServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSparseDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder


logging.basicConfig(level=logging.INFO)

class SlaveContexts:
    def __init__(self, slave_ids):
        self.contexts = {}  # dictionary of ModbusSlaveContext, key = slave_id
        try:
            for id in slave_ids:
                #print(f"ID: {id}")
                ctx = ModbusSlaveContext(
                    di=ModbusSparseDataBlock(),
                    co=ModbusSparseDataBlock(),
                    hr=ModbusSparseDataBlock(),
                    ir=ModbusSparseDataBlock(),
                )
                #print(f"ID: {ctx}")
                self.contexts[int(id)] = ctx
            #print(f"DATA : {input_data}")

        except:
            logging.error("failed in instantiating SparseDataBlock class")
    
    def update_context(self, slave_id):
        ctx = self.contexts[slave_id]
        data = self.__data[slave_id]
        template = self.__templates[slave_id]

        data.advance_data_point()

        for entry in template.modbus_entries:
            if entry.io_name == nan:
                continue  # skipping invalid io_name

            sim_data_index = data.headers.get(entry.io_name)
            sim_data_index_WD = sim_data_index
            if sim_data_index is None:
                simulated_value = 0
            else:
                simulated_value = data.get_data()[sim_data_index]
                logging.info(
                    "{} slave: {} | tag: {} \t- {}\t | value: {}".format(
                        datetime.now(),
                        slave_id,
                        entry.io_name,
                        int(entry.register_type) + int(entry.register_offset),
                        simulated_value,
                    )
                )

def updater_entrypoint(contexts, id, period):
    while 1:
        contexts.update_context(id)
        print("=========================================================================================")
        sleep(int(period))

def main():
    slave_contexts = SlaveContexts(slave_ids, input_data, modbus_templates)
    print(slave_contexts.contexts)
    store = ModbusServerContext(slaves=slave_contexts.contexts, single=False)

    for idx, id in enumerate(slave_ids):
        updater = threading.Thread(
            target=updater_entrypoint, args=(
                slave_contexts, int(id), periods[idx])
        )

        updater.daemon = True
        updater.start()

    StartSerialServer(
        store, framer=ModbusRtuFramer, port=args.port, timeout=0.05, baudrate=9600
    )


if __name__ == "__main__":
    main()
