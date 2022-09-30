import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from time import sleep

from scipy import stats
from scipy.optimize import minimize

from sklearn.metrics import r2_score

import pymodbus
from pymodbus.client.sync import ModbusSerialClient

import sys
import seaborn as sns

import slave
import subprocess
import runpy


def objective(x, a, b, c, wc):
    fun = (a*x**2 + b*x + c)*(1-wc)
    return -fun  # maximation


def objectives(x, a, b, c, wc):
    fun = (a*x**2 + b*x + c)*(1-wc)
    return fun  # minimation


def regress(x, a, b, c):
    fun = a*x**2 + b*x + c
    return fun


def constraint(x):
    return 1000 - x


def constraint2(x):
    return x/x - 1


con1 = {'type': 'ineq', 'fun': constraint}
con2 = {'type': 'eq', 'fun': lambda x: max(
    [x[i]-int(x[i]) for i in range(len(x))])}  # integer constraint
con = [con1]

# ========================================== DATA PREPROCESS ==========================================
df1 = pd.read_csv('well_cleaned_qt.csv')  # bisa sorted or not]
print(df1.head())

ff = list(range(8, 16, 2))
print(f"variasi batch data: {ff}")

r2_total = []  # r2 for each iteration
R2_all = []  # r2 for each day
rate = []
avg_all = []  # avg increase each iteration
avg_inc = []  # avg increase each day

ff = [8]  # test
print('======================= DATA-DRIVEN GAS LIFT INJECTION OPTIMIZER PREDICTION =======================\n')

for num in ff:

    x_glir = []
    yp = []
    yd = []

    x_glir_opt = []
    y_glir_opt = []

    y_optimal_qo = []
    y_comp = []
    x_comp = []
    wcd = []

    cond = []
    j = 0

    df_VX = pd.DataFrame({"qo_lc": [0], "qt_lc": [0], "wc": [0], "GLIR": [0]})
    df_ABB = pd.DataFrame({"GLIR": [0]})
    print(df_VX)

    #df_VX = pd.DataFrame({'qo_lc' : [0], 'qt_lc': [1], 'wc':[2], 'GLIR':[3]})
    #df_ABB = pd.DataFrame({'GLIR':[4]})

    data1 = df1.to_numpy()

    x1 = data1[:, 3]  # GLIR
    y1 = data1[:, 1]  # Qt
    z1 = data1[:, 0]  # Qo

    plt.figure(0)
    plt.plot(x1, y1, label='Ql')
    plt.plot(x1, z1, label='Qo')
    plt.grid()
    plt.legend()
    plt.xlabel('GLIR')
    plt.ylabel('Flow rate')
    plt.title("Flow Oil (Qo) vs Flow Liquid (Qt)")
    # plt.show()

    # ========================================== PARAMETERS ==========================================
    n_test = len(df1)
    n_train = num
    n = n_test-n_train
    # print(n)
    # n = 3

    for i in range(0, n+1):
        # ========================================== DATA SPLITTING ==========================================
        df = df1.iloc[i:i+n_train]
        # DF di sort untuk keperluan Regresi
        df_regresi = df1.iloc[i:i+n_train]
        df_reg = df_regresi.copy()
        df_reg.sort_values(by='GLIR', ascending=True, inplace=True)

        x_reg = df_reg['GLIR'].values  # Sorted GLIR Val Well a
        y_reg = df_reg['Qt'].values  # Sorted Qt Val Well a
        x_reg = np.insert(x_reg, 0, 0)
        y_reg = np.insert(y_reg, 0, 0)

        x = df['GLIR'].values  # GLIR
        y = df['Qt'].values  # Qt

        x1 = df['GLIR'].values  # GLIR
        x1 = np.insert(x1, 0, 0)

        y1 = df['Qt'].values  # Qt
        y1 = np.insert(y1, 0, 0)

        z = df['Qo'].values  # Qo
        wc = df['wc'].values  # wc
        date = df['Date'].values

        # ========================================== GLPC REGRESSION ==========================================
        poly = np.polyfit(x_reg, y_reg, 2)
        # Predict Qt
        y_pred = regress(x_reg, poly[0], poly[1], poly[2])

        # ========================================== OPTIMIZATION OBJ FUNC ==========================================

        b = (0.75*x[-2], 1*x[-2])  # normalize bounds
        bound = [b]

        x0 = x[-1]  # initial guess

        par = (poly[0], poly[1], poly[2], wc[-1])  # parameters

        if poly[0] < 0:
            sol = minimize(objective, x0, args=par, method='SLSQP',
                           bounds=bound, constraints=con)
        else:
            sol = minimize(objectives, x0, args=par, method='SLSQP',
                           bounds=bound, constraints=con)

        # ========================================== DATA HANDLING ==========================================

        # Qo to Plot
        y_obj_fun = objectives(x, poly[0], poly[1], poly[2], wc[-1])
        # Qt to Scatter Optimal Point
        y_optimal = regress(sol.x, poly[0], poly[1], poly[2])
        # Qo to Scatter Optimal Point
        yy = objectives(int(sol.x[0]), poly[0], poly[1], poly[2], wc[-1])
        # Qo from Data
        y_comparison = z[-1]

        if yy >= y_comparison:
            # print("[+]\tGLIR:", x[-1], "\tnilai Qo data:", y_comparison, "\tGLIR opt:", int(sol.x),"\tQo optimal model:", yy, "incr avg:", yy-y_comparison)
            cond.append("+")
            j = j+1
        else:
            # print("[-]\tGLIR:", x[-1], "\tnilai Qo data:", y_comparison, "\tGLIR opt:", int(sol.x),"\tQo optimal model:", yy, "incr avg:", yy-y_comparison)
            cond.append("-")

        avg_incc = yy-y_comparison
        avg_inc.append(avg_incc)

        y_optimal_qo.append(yy)
        y_comp.append(z[-1])
        x_comp.append(x[-1])

        x_glir.append(x)
        yp.append(y_pred)  # Qt predict
        yd.append(y[-1])       # Qt data
        wcd.append(wc[-1])

        x_glir_opt.append(int(sol.x))  # GLIR
        y_glir_opt.append(yy)  # Qt

        # ========================================== VISUALIZATION ==========================================
        """plt.figure(1)
        plt.plot(x, y_obj_fun)  # Qo plot
        plt.scatter(sol.x, yy)  # Qo point optimal
        plt.grid()
        plt.xlabel('GLIR')
        plt.ylabel('Ql')
        plt.title("Qo Regression Curve with Its Optimal Point")"""

        """plt.figure(5)
        sns.regplot(x=y_pred, y=y)
        plt.xlabel('Qt Pred')
        plt.ylabel('Qt Data')
        plt.title("Qt Data vs Qt Pred")"""

        plt.figure(6)
        plt.scatter(x_reg, y_pred)  # Qt plot
        plt.scatter(x_reg, y_reg)  # Qt point optimal
        plt.plot(np.arange(0, max(x), 25), regress(
            np.arange(0, max(x), 25), poly[0], poly[1], poly[2]))
        plt.grid()
        plt.xlabel('GLIR (MSCFD)')
        plt.ylabel('Qt (BFPD)')
        plt.title("Qt Regression Curve vs Qt Plot Data")
        # plt.show()

        # ========================================== R^2 SCORED ==========================================
        R = np.corrcoef(y1, y_pred, rowvar=False)[0, 1]
        R2 = R**2

        r2_total.append(R2)
        # print(f"Variasi n = {num} => R squared = {R2}")

        # ========================================== STORING VALUES INTO CSV ==========================================
        df_VX = df_VX.replace(to_replace=[df_VX['qo_lc'][0], df_VX['qt_lc'][0],
                              df_VX['wc'][0], df_VX['GLIR'][0]], value=[z[-1], y[-1], wc[-1], x[-1]])
        print(df_VX)

        df_ABB = df_ABB.replace(
            to_replace=[df_ABB['GLIR'][0]], value=[int(sol.x)])
        print(df_ABB)

        df_VX.to_csv("well_VX.csv")
        df_ABB.to_csv("well_ABB.csv")

        sleep(6)
        i += 1
    # ========================================== DATA FRAME ==========================================
    df_outlist = pd.DataFrame(list(zip(df1['Date'], cond, x_comp, y_comp, x_glir_opt, y_glir_opt, avg_inc)),
                              columns=['Date', 'Succes Status', 'GLIR data', 'Qo', 'GLIR Opt', 'Qo Opt', 'Avg Increase'])
    print(df_outlist)

    df_VX1 = pd.DataFrame(list(zip(df1['Date'], y_comp, yd, wcd, x_comp)), columns=[
        'Date', 'qo_lc', 'qt_lc', 'wc', 'GLIR'])
    print(df_VX1)

    df_ABB1 = pd.DataFrame(list(zip(df1['Date'], x_glir_opt)),
                           columns=['Date', 'GLIR'])
    print(df_ABB1)

    # df_VX.to_csv("well_VX.csv")
    # df_ABB.to_csv("well_ABB.csv")
    # ========================================== MODBUS SLAVE PARSER ==========================================
    # cmd = 'python slave.py -s 113 -i well_new.csv -m VX.xlsx -pd 1 -po COM1'
    # p = subprocess.Popen(cmd, shell=True)

    # print(r2_total)
    inc_avg = sum(avg_inc)/len(avg_inc)
    r2_avg = sum(r2_total)/len(r2_total)
    print(f"AVERAGE R Squared for {n+1}th day is {r2_avg}")
    print(f"AVERAGE INCREASE Squared for {n+1}th day is {inc_avg}")

    # R2 Average
    R2_all.append(r2_avg)
    avg_all.append(inc_avg)

    r = (j/(n+1))*100
    print("JUMLAH DATA OPTIMAL=", j, "dari total:", n+1,
          "data", "\t rate:", r, "%")
    rate.append(r)

    x_glir = np.reshape(x_glir, (n+1, -1))
    yp = np.reshape(yp, (n+1, -1))
    yd = np.reshape(yd, (n+1, -1))

    x_glir_opt = np.reshape(x_glir_opt, (n+1, -1))
    y_glir_opt = np.reshape(y_glir_opt, (n+1, -1))

    y_optimal_qo = np.reshape(y_optimal_qo, (n+1, -1))

    print("===========================================================================================\n")

    plt.figure(2)
    sns.regplot(x=y_comp, y=y_optimal_qo)
    plt.xlabel('Qo Data')
    plt.ylabel('Qo Pred')
    plt.title("Qo Data vs Qo Pred")

    plt.figure(3)
    plt.plot(np.arange(0, n+1), np.asarray(y_comp), label='Qo Data')
    plt.plot(np.arange(0, n+1), y_optimal_qo, label='Qo Pred')
    # plt.plot(np.arange(0, n), np.asarray(x_comp), label='GLIR Data')
    # plt.plot(np.arange(0, n), x_glir_opt, label='GLIR Pred')
    plt.legend()
    plt.grid()
    plt.legend()
    plt.xlabel('num of iteration')
    plt.ylabel('Ql')
    plt.title(
        " Comparison of Qo data, GLIR data to Qo Prediction, GLIR Pred each Iteration ")

    avg_inc = []
    num += 1

dff = pd.DataFrame(list(zip(ff, R2_all, avg_all, rate)), columns=[
                   'Variation', 'R2 average', 'Average Increace', 'Rate'])
print(dff)
print(f"\nBEST value from FITNESS RATE is on row: {dff['Rate'].idxmax()}-th")


# plt.show()
