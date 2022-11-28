import argparse
import csv
from datetime import datetime
import logging
from math import nan
import threading
import pandas
import random
 
from time import sleep
from pymodbus.server.sync import StartSerialServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSparseDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder
 
 
logging.basicConfig(level=logging.INFO)
 
class ModbusEntry:
    __r_length = {
        "UNSIGNED INT": 1,
        "INT": 1,
        "FLOAT": 2,
        "DISCRETE": 1,
        "BOOLEAN": 1,
        "BYTE": 1,
        "UNSIGNED BYTE": 1,
        "DOUBLE": 4,
        "LONG": 2,
        "SIGNED LONG": 2,
        "UNSIGNED LONG": 2,
    }
 
    __endiannes = {
        "4321": {
            "byte_order": Endian.Big,
            "word_order": Endian.Big,
        },
        "1234": {
            "byte_order": Endian.Little,
            "word_order": Endian.Little,
        },
        "2143": {
            "byte_order": Endian.Big,
            "word_order": Endian.Little,
        },
        "3412": {
            "byte_order": Endian.Little,
            "word_order": Endian.Big,
        },
    }
 
    __DESCRIPTION = 0  # string
    __IO_NAME = 1  # string
    __DATA_TYPE = 2  # UNSIGNED INT, FLOAT, DISCRETE, BOOLEAN, INT, SIGNED INT, BYTE, UNSIGNED BYTE, DOUBLE, LONG, SIGNED LONG, UNSIGNED LONG
    __REGISTER_TYPE = 3  # 0, 10000, 30000, 40000 | discrete, coil, input, holding
    __REGISTER_OFFSET = 4  # 4 number
    __ENDIANNES = 5  # 4321, 1234, 3412, 2143
    __IO_TYPE = 6  # R, W, RW
    __UNIT = 8
 
    def __init__(self, row):
        try:
            if len(row) < 6:
                raise Exception("row data length less than required")
            self.description = str(row[self.__DESCRIPTION]).strip()
            self.io_name = str(row[self.__IO_NAME]).strip()
            self.data_type = str(row[self.__DATA_TYPE]).strip()
            self.register_length = self.__r_length[str(
                row[self.__DATA_TYPE]).strip()]
            self.register_type = str(row[self.__REGISTER_TYPE]).strip()
            self.register_offset = str(row[self.__REGISTER_OFFSET]).strip()
            self.endiannes = self.__endiannes[str(int(row[self.__ENDIANNES]))]
            self.io_type = str(row[self.__IO_TYPE])
            self.unit = str(row[self.__UNIT])
        except:
            pass
 
class ModbusTemplate:
    def __init__(self, path):
        """try:
            excel_data = pandas.read_excel(path, skiprows=3)
        except:
            print('FAILED READING')"""
        excel_data = pandas.read_excel(path, skiprows=3)
        self.modbus_entries = []
        for row in excel_data.values:
            #print(f"NILAI ROW: {row}")
            entry = ModbusEntry(row)
            #print(f"NILAI ROW: {entry}")
            self.modbus_entries.append(entry)
 
class SlaveContexts:
    def __init__(self, slave_ids,modbus_templates,val_data):
        self.contexts = {}  # dictionary of ModbusSlaveContext, key = slave_id
        #self.val_data = {}
        try:
            self.__templates = (modbus_templates)  # dictionary of ModbusTemplate, key = slave_id
            self.__val_data = (val_data)
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
   
    def update_context(self, slave_id,val_data):
        ctx = self.contexts[slave_id]
        template = self.__templates[slave_id]
        values = self.__val_data[slave_id]
       
        for entry in template.modbus_entries:
            if slave_id == 113:
                if entry.register_type == "30000" and int(entry.register_offset) == 167: # Qw VX
                #if 1 == 1:
                    #print(f"SLAVE IDs inside loop : {slave_id}")
                    simulated_value = round(values,3)
                   
                    # ========================================== SET VALUES to REGISTER ==========================================
                    register_values = self.__pack_by_endiannes(
                        simulated_value, entry.endiannes, entry.data_type)
                    #print(f"Slave - {slave_id} REGISTER VAL: {register_values}")
                    ctx.store["i"].setValues(int(entry.register_offset) + 1, register_values)
                    #ctx.setValues(3,int(entry.register_type) + int(entry.register_offset), [45])
                    #qt = ctx.store["h"].getValues(int(entry.register_type) + int(entry.register_offset), count=1)
 
                else:
                    continue
            elif slave_id ==114:
                if entry.register_type == "40000" and int(entry.register_offset) == 7036: #GLIR ABB
                    #print(f"SLAVE IDs inside loop : {slave_id}")
                    simulated_value = WellDyn(values, -0.001, 1.4, 110, 5)
                    simulated_value = int(simulated_value)
                   
                    # ========================================== SET VALUES to REGISTER ==========================================
                    register_values = self.__pack_by_endiannes(
                        simulated_value, entry.endiannes, entry.data_type)
                    #print(f"Slave - {slave_id} REGISTER VAL: {register_values}")
                    ctx.store["h"].setValues(int(entry.register_offset) + 1, register_values)
                    #qt = ctx.store["h"].getValues(int(entry.register_offset) + 1, count=1)
                    #print(qt)
                else:
                    continue
            else:
                continue
            # ========================================== LOG VALUEs ==========================================
            #print(f"Slave - {slave_id} \t | REGISTER VAL: {register_values}")
            logging.info(
                    "{} slave: {} | tag: {} \t- {}\t | value: {} {}".format(
                        datetime.now(),
                        slave_id,
                        entry.io_name,
                        int(entry.register_type) + int(entry.register_offset),
                        simulated_value,
                        entry.unit
                    )
                )
 
    def __pack_by_endiannes(self, val, endiannes, data_type):
        builder = BinaryPayloadBuilder(
            byteorder=endiannes["byte_order"], wordorder=endiannes["word_order"]
        )
 
        if val == "":  # set to 0 if empty string
            val = 0
 
        if data_type == "UNSIGNED INT":
            builder.add_16bit_uint(int(val))
        elif data_type == "INT":
            builder.add_16bit_int(int(val))
        elif data_type == "FLOAT":
            builder.add_32bit_float(float(val))
        elif data_type == "DISCRETE":
            builder.add_bits(int(val))
        elif data_type == "BOOLEAN":
            builder.add_bits(int(val))
        elif data_type == "BYTE":
            builder.add_8bit_int(int(val))
        elif data_type == "UNSIGNED BYTE":
            builder.add_8bit_uint(int(val))
        elif data_type == "DOUBLE":
            builder.add_64bit_float(float(val))
        elif data_type == "LONG":
            builder.add_32bit_int(int(val))
        elif data_type == "UNSIGNED LONG":
            builder.add_32bit_uint(int(val))
 
        return builder.to_registers()
 
def WellDyn(GLIR,a,b,c,e):
    Qt = a*(GLIR**2) + b*(GLIR) + c
    Qt_rand = Qt + Qt*random.uniform(-e/100, e/100)
    return Qt_rand
 
def updater_entrypoint(contexts, id, period, val_data):
    while 1:
        FX_MAPPER = {
        "coils": 1,
        'discrete_inputs': 2,
        'input_registers': 3,
        'holding_registers': 4
        }
 
        # ========================================== WELL DYNAMICS (f_Qt(GLIR)) ==========================================
        a = contexts.contexts[114].getValues(4,47036,count=1) #GLIR
        #print(f"GLIR OPTIMAL from SOLVER: {a}")
        b = WellDyn(a[0], -0.001, 1.4, 110, 5)
        contexts.contexts[113].setValues(3,30167,[b])
 
        #b = contexts.contexts[113l].getValues(3,47009,count=1)
        #print(f"GLIR VALUE:\t {a[0]} mscfd\nQt VALUE :\t {b} bopd")
       
        #store_ctx = [a[0],b]
        if id == 113:
            val_data[id] = a[0]
        elif id == 114:
            val_data[id] = b
        else:
            continue
 
        # ========================================== STORE to REGISTERS ==========================================
        #print(f"VAL DATA DICT: {val_data}")
        contexts.update_context(id,val_data)
 
        # ========================================== GLIR INPUT SIMULATED ==========================================
        #Simulation of Changing GLIR Setpoints should be changed by the value written by master.py
        if id == 114:
            temp_a = [random.uniform(500, 800)]
            contexts.contexts[114].setValues(4,47036,temp_a)
            #print(f"GLIR OPTIMAL: {temp_a}")
        else:
            1 == 1
        #print("=================================================================================================")
        sleep(int(period))
 
def main():
 
    #Context Slave yg menyimpan di datasotre
    slave_ids = [113,114]
    input_data = [0,1]
    periods = [1,1]
    modbus_template_paths = ['VX1.xlsx','ABB.xlsx']
   
    # ========================================== LOOPING SLAVE IDs ==========================================
    modbus_templates = {}
    val_data = {}
   
    for idx, id in enumerate(slave_ids):
        #print(id)
        #print(modbus_template_paths[idx])
        #print(input_data[idx])
       
        template = ModbusTemplate(modbus_template_paths[idx])
        val_data[int(id)] = input_data[idx]
        modbus_templates[int(id)] = template
       
        logging.info(
            "simulating slave id {} with init. condition {} from {}".format(
                id, input_data[idx], modbus_template_paths[idx]
            )
        )
   
    print(template)
    print(f"TYPE MODTEMP: {modbus_templates}")
    print(f"TYPE VALDATA: {val_data}")
    # ========================================== SETTING UP CONTEXT ==========================================
    slave_contexts = SlaveContexts(slave_ids,modbus_templates,val_data)
    store = ModbusServerContext(slaves=slave_contexts.contexts, single=False)
 
    print(f"CTX: {slave_contexts}")
    print(f"STORE: {store}\n \n")
    # ========================================== INITIAL CONDITION ==========================================
    slave_contexts.contexts[113].setValues(3,30167,[val_data[113]]) #coba pake enumerate dan loop nanti
    slave_contexts.contexts[114].setValues(4,47036,[val_data[114]])
 
    # ========================================== THREADING EACH SLAVE IDs ==========================================
    for idx, id in enumerate(slave_ids):
        updater = threading.Thread(
            target=updater_entrypoint, args=(
                slave_contexts, int(id), periods[idx], val_data)
        )
 
        updater.daemon = True
        updater.start()
 
    StartSerialServer(
        store, framer=ModbusRtuFramer, port='COM6', timeout=0.05, baudrate=9600
    )
 
 
if __name__ == "__main__":
    main()
