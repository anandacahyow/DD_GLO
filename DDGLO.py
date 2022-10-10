import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from time import sleep

from scipy import stats
from scipy.optimize import minimize

from sklearn.metrics import r2_score

import sys
import seaborn as sns

from gekko import GEKKO


class DDGLO():
    def __init__(self, dataset, i,param):  # param yg bakal dipake (dataset, )
        self.dataset = dataset
        self.i = i
        self.param=param
    
    def DataRef(self,param):
        DF = pd.read_csv(self.dataset)
        data_csv = DF[self.param].values
        data = data_csv[self.i]
        return data

    def RegOpt(self, i):
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
        df1 = pd.read_csv(self.dataset)  # bisa sorted or not]
        # print(df1.head())

        ff = list(range(8, 16, 2))
        #print(f"variasi batch data: {ff}")

        r2_total = []  # r2 for each iteration
        R2_all = []  # r2 for each day
        rate = []
        avg_all = []  # avg increase each iteration
        avg_inc = []  # avg increase each day

        ff = [8]  # test
        #print('======================= DATA-DRIVEN GAS LIFT INJECTION OPTIMIZER PREDICTION =======================\n')

        # ========================================== PARAMETERS ==========================================
        n_test = len(df1)
        n_train = 8
        n = n_test-n_train
        # print(n)
        # n = 3

        df = df1.iloc[self.i:self.i+n_train]
        # DF di sort untuk keperluan Regresi
        df_regresi = df1.iloc[self.i:self.i+n_train]
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
            sol = minimize(objective, x0, args=par,
                           method='SLSQP', bounds=bound, constraints=con)
        else:
            sol = minimize(objectives, x0, args=par,
                           method='SLSQP', bounds=bound, constraints=con)

        # ========================================== DATA HANDLING ==========================================
        # Qo to Plot
        y_obj_fun = objectives(x, poly[0], poly[1], poly[2], wc[-1])
        # Qt to Scatter Optimal Point
        y_optimal = regress(sol.x, poly[0], poly[1], poly[2])
        # Qo to Scatter Optimal Point
        yy = objectives(int(sol.x[0]), poly[0],
                        poly[1], poly[2], wc[-1])
        # Qo from Data
        y_comparison = z[-1]

        # ========================================== R^2 SCORED ==========================================
        R = np.corrcoef(y1, y_pred, rowvar=False)[0, 1]
        R2 = R**2

        r2_total.append(R2)

        output = [z[-1], y[-1], wc[-1], x[-1], int(sol.x),yy]

        return output

class WellDyn():
    def __init__(self, u,i,u2):  # param yg bakal dipake (dataset, )
        self.u = u
        self.i = i
        self.u2 = u2
        #self.header=header

    def WellSys(self,u,i,u2):
        import control as ctl
        
        DF = pd.read_csv(self.u2)
        data = DF['Qt'].values
        qt1 = data[0:self.i+1]
        #qt1.tolist()
        #qt = qt1[self.i]

        #t = np.arange(0,3600*24*len(self.u),3600*24)
        
        if np.shape(self.u) == (1,):
            x_ident = [0,0,self.u[0]]
        elif np.shape(self.u) == (2,):
            x_ident = [0,self.u[0],self.u[1]]
        else:
            x_ident1 = [0,self.u[0],self.u[1]]
            x_ident_temp = x_ident1.copy()
            x_ident = x_ident_temp + self.u[2:self.i+1]
        
        if len(qt1) == 1:
            x_dident = [0,0,qt1[0]]
        elif len(qt1) == 2:
            x_dident = [0,qt1[0],qt1[1]]
        else:
            x_dident1 = [0,qt1[0],qt1[1]]
            x_dident_temp = x_dident1.copy()
            x_dident = x_dident_temp + qt1[2:self.i+1].tolist()
        
        u_sys = np.subtract(np.array(x_dident),np.array(x_ident))
        #u_sys = np.subtract(np.array(x_ident),np.array(self.temp))
        #u_sys.tolist()

        #zero delay
        num = np.array([0.3678,-0.3667])
        den = np.array([1.0000,-1.3745,0.4767,-0.0976])

        #second order delay
        num = np.array([0.343188420833007,-0.343090293948511,0,0])
        den = np.array([1,-1.369332042280427,0.473411287445827,-0.101420313022513]) 

        #second order delay ARX
        #num = np.array([0,0,0.291967330160550,-0.242849422368530])
        #den = np.array([1,-0.690217748679766,0.081126624658709,-0.287692951198518]) 

        K = 1.5
        K = 2
        Ts = 3600*24  #1 day sampling day
        sys = ctl.TransferFunction(K*num,den, dt=Ts)

        res = ctl.forced_response(sys,T=None,U=u_sys,X0=0)
        y_sys = res.outputs
        x_sys = res.inputs
        
        return y_sys

if __name__ == "__main__":
    main()
