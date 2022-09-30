# DD_GLO

How To Run
\n1. Run the slave using command below on cmd: *you may choose one
\n================================SLAVE===========================
\nall:
python slave.py -s 113,114 -i well_VX1.csv,well_ABB.csv -m VX1.xlsx,ABB.xlsx -pd 3,3 -po COM6
\nholding reg. only:
python slave.py -s 114 -i well_new_GLIR.csv -m ABB1.xlsx -pd 3 -po COM6
\n================================================================

\n2. Then, Run the Master using command below on cmd:
\n================================MASTER==========================
python master.py -po COM7
\n================================================================
