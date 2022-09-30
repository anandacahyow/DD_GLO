# DD_GLO

How To Run
1. Run the slave using command below on cmd: *you may choose one
================================SLAVE===========================
all:
python slave.py -s 113,114 -i well_VX1.csv,well_ABB.csv -m VX1.xlsx,ABB.xlsx -pd 3,3 -po COM6

holding reg. only:
python slave.py -s 114 -i well_new_GLIR.csv -m ABB1.xlsx -pd 3 -po COM6
================================================================

2. Then, Run the Master using command below on cmd:
================================MASTER==========================
python master.py -po COM7
================================================================
