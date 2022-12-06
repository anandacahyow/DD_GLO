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
    def __init__(self, GLIR, Qt, wc, GLIR2, Qt2, wc2, i):  # list of GLIR and Qt
        self.GLIR = GLIR
        self.Qt = Qt
        self.wc = wc
        self.i = i
        self.GLIR2 = GLIR2
        self.Qt2 = Qt2
        self.wc2 = wc2
    
    def RegOpt(self):
        def objective(x, a, b, c, wc, a2, b2, c2, wc2):
            x1 = x[0]
            x2 = x[1]
            fun = (a*x1**2 + b*x1 + c)*(1-wc) + (a2*x2**2 + b2*x2 + c2)*(1-wc2)
            return -fun  # maximation


        def objectives(x, a, b, c, wc, a2, b2, c2, wc2):
            x1 = x[0]
            x2 = x[1]
            fun = (a*x1**2 + b*x1 + c)*(1-wc) + (a2*x2**2 + b2*x2 + c2)*(1-wc2)
            return fun  # minimation
        
        def regress(x, a, b, c):
            fun = a*x**2 + b*x + c
            return fun

        def constraint(x):
            x1 = x[0]
            x2 = x[1]
            return 2000 - x1 - x2

        def constraint2(x):
            return x/x - 1

        con1 = {'type': 'ineq', 'fun': constraint}
        con2 = {'type': 'eq', 'fun': lambda x: max(
            [x[i]-int(x[i]) for i in range(len(x))])}  # integer constraint
        con = [con1]

        # ========================================== DATA PREPROCESS ==========================================
        ff = list(range(8, 16, 2))
        #print(f"variasi batch data: {ff}")

        ff = [8]  # test
        #print('======================= DATA-DRIVEN GAS LIFT INJECTION OPTIMIZER PREDICTION =======================\n')

        # ========================================== PARAMETERS ==========================================
        n_train = 8

        x = self.GLIR[self.i:self.i+n_train]
        y = self.Qt[self.i:self.i+n_train]
        x_reg = self.GLIR[self.i:self.i+n_train]
        y_reg = self.Qt[self.i:self.i+n_train]
        x_reg.sort()
        y_reg.sort()
        x_reg = np.insert(x_reg, 0, 0)
        y_reg = np.insert(y_reg, 0, 0)

        x2 = self.GLIR2[self.i:self.i+n_train]
        y2 = self.Qt2[self.i:self.i+n_train]
        x_reg2 = self.GLIR2[self.i:self.i+n_train]
        y_reg2 = self.Qt2[self.i:self.i+n_train]
        x_reg2.sort()
        y_reg2.sort()
        x_reg2 = np.insert(x_reg2, 0, 0)
        y_reg2 = np.insert(y_reg2, 0, 0)

        wc = self.wc
        wc2 = self.wc2

        # ========================================== GLPC REGRESSION ==========================================
        poly = np.polyfit(x_reg, y_reg, 2)
        poly2 = np.polyfit(x_reg2, y_reg2, 2)
        # ========================================== REGRESSION CONDITIONING ==========================================
        if poly[0] > 0:
            if poly[1] > 0 and poly[2] > 0:
                y_pred = regress(x_reg,-poly[0], -poly[1], -poly[2])
                y_pred2 = regress(x_reg2,-poly2[0], -poly2[1], -poly2[2])
                par = (-poly[0], -poly[1], -poly[2], wc,-poly2[0], -poly2[1], -poly2[2], wc2)
                #print("c1:", [-poly[0], poly[1], poly[2]])

            elif poly[1] > 0 and poly[2] < 0:
                y_pred = regress(x_reg,-poly[0], -poly[1], poly[2])
                y_pred2 = regress(x_reg2,-poly2[0], -poly2[1], poly2[2])
                par = (-poly[0], -poly[1], poly[2], wc,-poly2[0], -poly2[1], poly2[2],wc2)
                #print("c2:", [-poly[0], poly[1], -poly[2]])

            elif poly[1] < 0 and poly[2] > 0:
                y_pred = regress(x_reg,-poly[0], -poly[1], poly[2])
                y_pred2 = regress(x_reg2,-poly2[0], -poly2[1], poly2[2])
                par = (-poly[0], -poly[1], poly[2], wc, -poly2[0], -poly2[1], poly2[2], wc2)
                #print("c3:", [-poly[0], -poly[1], poly[2]])

            #elif poly[1] < 0 and poly[2] < 0:
            else:
                y_pred = regress(x_reg,-poly[0], -poly[1], -poly[2])
                y_pred2 = regress(x_reg2,-poly2[0], -poly2[1], -poly2[2])
                par = (-poly[0], -poly[1], -poly[2], wc, -poly2[0], -poly2[1], -poly2[2], wc2)
                #print("c4:", [-poly[0], -poly[1], -poly[2]])
        else:
            y_pred = regress(x_reg,poly[0], poly[1], poly[2])
            y_pred2 = regress(x_reg2,poly2[0], poly2[1], poly2[2])
            par = (poly[0], poly[1], poly[2], wc, poly2[0], poly2[1], poly2[2], wc2)
            #print("c5:", poly[0], poly[1], poly[2])

        # ========================================== OPTIMIZATION OBJ FUNC ==========================================

        b = (0.75*x[-2], 1*x[-2])  # normalize bounds
        b2 = (0.75*x2[-2], 1*x2[-2])  # normalize bounds
        bound = [b,b2]

        x0 = [x[-1],x2[-1]]  # initial guess

        if poly[0] < 0:
            sol = minimize(objective, x0, args=par,
                           method='SLSQP', bounds=bound, constraints=con)
        else:
            sol = minimize(objectives, x0, args=par,
                           method='SLSQP', bounds=bound, constraints=con)
        solx = [int(sol.x[0]),int(sol.x[1])]
        # ========================================== DATA HANDLING ==========================================
        # Qo to Plot
        #y_obj_fun = objectives(x, poly[0], poly[1], poly[2], wc)
        # Qt to Scatter Optimal Point
        y_optimal = regress(solx[0], poly[0], poly[1], poly[2])
        y_optimal2 = regress(solx[1], poly2[0], poly2[1], poly2[2])
        # Qo to Scatter Optimal Point
        #yy = objectives(int(sol.x[0]), poly[0],poly[1], poly[2], wc)
        # Qo from Data
        #y_comparison = z[-1]

        print('SOLUTION', solx)

        output = [solx[0],solx[1], y_optimal, y_optimal2, x_reg, x_reg2, y_pred, y_pred2]

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

        #y_sys = 2*x_dident + u_sys
        
        return y_sys

class WellDynSys():
    def __init__(self, u,i):  # param yg bakal dipake (dataset, )
        self.u = u
        self.i = i
        #self.header=header

    def WellSys(self,u,i):
        import control as ctl
        
        if np.shape(self.u) == (1,):
            x_ident = [0,0,self.u[0]]
        elif np.shape(self.u) == (2,):
            x_ident = [0,self.u[0],self.u[1]]
        else:
            x_ident1 = [0,self.u[0],self.u[1]]
            x_ident_temp = x_ident1.copy()
            x_ident = x_ident_temp + self.u[2:self.i+1]
            
        #u_sys = np.subtract(np.array(x_dident),np.array(x_ident))
        u_sys = x_ident
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

        #y_sys = 2*x_dident + u_sys
        
        return y_sys

if __name__ == "__main__":
    main()
