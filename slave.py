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
        except:
            pass


class ModbusTemplate:
    def __init__(self, path):
        excel_data = pandas.read_excel(path, skiprows=3)
        self.modbus_entries = []
        for row in excel_data.values:
            entry = ModbusEntry(row)
            self.modbus_entries.append(entry)


class InputData:
    def __init__(self, csv_path):
        self.headers = {}
        self.data = []
        self.current_idx = 0

        with open(csv_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")
            for id, row in enumerate(csv_reader):
                if id == 0:
                    for idx, val in enumerate(row):
                        self.headers[val] = idx
                else:
                    self.data.append(row)

    def advance_data_point(self):
        if self.current_idx < len(self.data) - 1:
            self.current_idx += 1
        else:
            self.current_idx = 0

    def get_data(self):
        return self.data[self.current_idx]


class SlaveContexts:
    def __init__(self, slave_ids, input_data, modbus_templates):
        self.contexts = {}  # dictionary of ModbusSlaveContext, key = slave_id
        try:
            self.__data = input_data  # dictionary of InputData, key = slave_id
            self.__templates = (
                modbus_templates  # dictionary of ModbusTemplate, key = slave_id
            )

            for id in slave_ids:
                ctx = ModbusSlaveContext(
                    di=ModbusSparseDataBlock(),
                    co=ModbusSparseDataBlock(),
                    hr=ModbusSparseDataBlock(),
                    ir=ModbusSparseDataBlock(),
                )
                self.contexts[int(id)] = ctx

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

            register_values = self.__pack_by_endiannes(
                simulated_value, entry.endiannes, entry.data_type
            )

            if entry.register_type == "0":
                ctx.store["d"].setValues(
                    int(entry.register_offset) + 1, register_values
                )
            elif entry.register_type == "10000":
                ctx.store["c"].setValues(
                    int(entry.register_offset) + 1, register_values
                )
            elif entry.register_type == "30000":
                ctx.store["i"].setValues(
                    int(entry.register_offset) + 1, register_values
                )
            elif entry.register_type == "40000":
                ctx.store["h"].setValues(
                    int(entry.register_offset) + 1, register_values
                )
            else:
                continue  # skipping invalid entry

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


def updater_entrypoint(contexts, id, period):
    while 1:
        contexts.update_context(id)
        sleep(int(period))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--slaves",
        help="slave id(s) to be simulated, comma separated",
        dest="slaves",
        required=True,
    )
    parser.add_argument(
        "-i",
        "--inputs",
        help="input csv file(s), comma separated",
        dest="inputs",
        required=True,
    )
    parser.add_argument(
        "-m",
        "--modbus-template",
        help="modbus template excel file(s), comma separated",
        dest="modbus_templates",
        required=True,
    )
    parser.add_argument(
        "-pd",
        "--periods",
        help="period in second to advance the data to the next data point, comma separated",
        dest="periods",
        required=True,
    )
    parser.add_argument(
        "-po", "--port", help="serial port to use", dest="port", required=True
    )

    args = parser.parse_args()
    input_data_paths = args.inputs.split(",")
    modbus_template_paths = args.modbus_templates.split(",")
    periods = args.periods.split(",")
    slave_ids = args.slaves.split(",")
    print(parser)

    if (
        not len(input_data_paths)
        == len(modbus_template_paths)
        == len(slave_ids)
        == len(periods)
    ):
        raise Exception(
            "length of input data path, modbus template path, slave ids, and periods don't match"
        )

    input_data = {}
    modbus_templates = {}

    for idx, id in enumerate(slave_ids):
        data = InputData(input_data_paths[idx])
        template = ModbusTemplate(modbus_template_paths[idx])
        input_data[int(id)] = data
        modbus_templates[int(id)] = template
        logging.info(
            "simulating slave id {} from {} and {}".format(
                id, input_data_paths[idx], modbus_template_paths[idx]
            )
        )

    slave_contexts = SlaveContexts(slave_ids, input_data, modbus_templates)
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
