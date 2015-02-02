# Size of variable arrays:
sizeAlgebraic = 13
sizeStates = 7
sizeConstants = 37

inputID = 34 # ID of the input quantity, which is the wall strain calculated in STARFiSh
outputArray = "algebraic" # array in which the output (heart period) of the BR model is found
outputID = 12 # id of heart period in output array

# Prevent style checking of autogenerated code
# pylint: disable-all
from math import *
from numpy.core import *
from matplotlib.cbook import iterable
from scipy.optimize import fsolve
def createLegends():
    legend_y = [""] * sizeStates
    legend_ydot = [""] * sizeStates
    legend_alg = [""] * sizeAlgebraic
    legend_t = ""
    legend_p = [""] * sizeConstants
    legend_t = "Time in component Environmental (second)"
    legend_p[0] = "S in component Parameters (hertz)"
    legend_p[1] = "Zeta in component Parameters (dimensionless)"
    legend_p[2] = "Cwall in component Parameters (mm_per_mmHg)"
    legend_p[3] = "Kne in component Parameters (mmHg_per_mm)"
    legend_p[4] = "K1 in component Parameters (mmHg_per_mm)"
    legend_p[5] = "K2 in component Parameters (mmHg_per_mm)"
    legend_p[6] = "K3 in component Parameters (mmHg_per_mm)"
    legend_p[7] = "Bwall in component Parameters (mmHg_s_per_sq_mm)"
    legend_p[8] = "B1 in component Parameters (mmHg_s_per_mm)"
    legend_p[9] = "B2 in component Parameters (mmHg_s_per_mm)"
    legend_p[10] = "B3 in component Parameters (mmHg_s_per_mm)"
    legend_p[11] = "Tsmax in component Parameters (AU)"
    legend_p[12] = "Tpmax in component Parameters (AU)"
    legend_p[13] = "Tsmin in component Parameters (AU)"
    legend_p[14] = "Tpmin in component Parameters (AU)"
    legend_p[15] = "Gcns in component Parameters (dimensionless)"
    legend_p[16] = "Gs in component Parameters (per_Hertz)"
    legend_p[17] = "Gp in component Parameters (per_Hertz)"
    legend_p[18] = "tau_nor in component Parameters (second)"
    legend_p[19] = "tau_ach in component Parameters (second)"
    legend_p[20] = "tau_HR_nor in component Parameters (second)"
    legend_p[21] = "tau_HR_ach in component Parameters (second)"
    legend_p[22] = "HRo in component Parameters (Beats_per_min)"
    legend_p[23] = "HRmax in component Parameters (Beats_per_min)"
    legend_p[24] = "HRmin in component Parameters (Beats_per_min)"
    legend_p[25] = "Beta in component Parameters (dimensionless)"
    legend_p[26] = "delta_th in component Parameters (dimensionless)"
    legend_p[27] = "q_nor in component Parameters (per_s)"
    legend_p[28] = "q_ach in component Parameters (per_s)"
    legend_p[29] = "K_nor in component Parameters (AU)"
    legend_p[30] = "K_ach in component Parameters (AU)"
    legend_p[31] = "Gamma in component Parameters (dimensionless)"
    legend_alg[5] = "alpha_cns in component Nervous_System (hertz)"
    legend_alg[3] = "n in component Nervous_System (hertz)"
    legend_alg[0] = "Delta in component Coupling_Dynamics (dimensionless)"
    legend_p[32] = "alpha_s0 in component Nervous_System (hertz)"
    legend_p[33] = "alpha_p0 in component Nervous_System (hertz)"
    legend_y[0] = "Eps_1 in component Coupling_Dynamics (dimensionless)"
    legend_y[1] = "Eps_2 in component Coupling_Dynamics (dimensionless)"
    legend_y[2] = "Eps_3 in component Coupling_Dynamics (dimensionless)"
    legend_p[34] = "Eps_wall in component Coupling_Dynamics (dimensionless)"
    legend_alg[7] = "Ts in component PNS_tones (AU)"
    legend_alg[8] = "Tp in component PNS_tones (AU)"
    legend_y[3] = "c_nor in component Norepinephrine (AU)"
    legend_y[4] = "C_ach in component Acetylcholine (AU)"
    legend_alg[1] = "delta_HR_ss in component Heart_Response_Nor (Beats_per_min)"
    legend_p[35] = "delta_HR_smax in component Heart_Response_Nor (Beats_per_min)"
    legend_y[5] = "delta_HR_s in component Heart_Response_Nor (Beats_per_min)"
    legend_alg[2] = "delta_HR_ps in component HR_ach (Beats_per_min)"
    legend_p[36] = "delta_HR_pmax in component HR_ach (Beats_per_min)"
    legend_alg[4] = "delta_HR_pfast in component HR_ach (Beats_per_min)"
    legend_y[6] = "delta_HR_pslow in component HR_ach (Beats_per_min)"
    legend_alg[6] = "delta_HR_p in component HR_ach (Beats_per_min)"
    legend_alg[11] = "HR in component HR_Combined (Beats_per_min)"
    legend_alg[10] = "HR_p in component HR_Combined (Beats_per_min)"
    legend_alg[9] = "HR_s in component HR_Combined (Beats_per_min)"
    legend_alg[12] = "Period in component HR_Combined (Sec_per_Beat)"
    legend_ydot[0] = "d/dt Eps_1 in component Coupling_Dynamics (dimensionless)"
    legend_ydot[1] = "d/dt Eps_2 in component Coupling_Dynamics (dimensionless)"
    legend_ydot[2] = "d/dt Eps_3 in component Coupling_Dynamics (dimensionless)"
    legend_ydot[3] = "d/dt c_nor in component Norepinephrine (AU)"
    legend_ydot[4] = "d/dt C_ach in component Acetylcholine (AU)"
    legend_ydot[5] = "d/dt delta_HR_s in component Heart_Response_Nor (Beats_per_min)"
    legend_ydot[6] = "d/dt delta_HR_pslow in component HR_ach (Beats_per_min)"
    return legend_y, legend_alg, legend_t, legend_p

def initConsts(t=0):
    p = zeros(sizeConstants)
    y = zeros(sizeStates)
    alg = zeros(sizeAlgebraic)
    p[0] = 480 # S
    p[1] = 1 # zeta
    p[2] = 0.006 # Cwall
    p[3] = 1 # Kne
    p[4] = 1.5 # K1
    p[5] = 3.75 # K2
    p[6] = 1.05 # K3
    p[7] = 1 # Bwall
    p[8] = 1 # B1
    p[9] = 10 # B2
    p[10] = 206.973 # B3
    p[11] = 4.12 #4.12 # Tsmax
    p[12] = 4.994 # Tpmax
    p[13] = 0.5 # Tsmin
    p[14] = 1.6 # Tpmin
    p[15] = 1 # Gcns
    p[16] = 0.178 # Gs
    p[17] = 0.492 # Gp
    p[18] = 9.1 # tau_nor
    p[19] = 0.2 # tau_ach
    p[20] = 2.1 # tau_HR_nor
    p[21] = 2.5 # tau_HR_ach
    p[22] = 107 #282.648 # HR zero - intrinsic heart rate ## 107 beats/min in 20 year old 90 in beats/min in 50 year old Opthof paper
    p[23] = 194 #483.218 #208 - 0.7 * age : Tanaka paper
    p[24] = 50 #226.238 # HR min - min heart rate  # might depend on fitness level 35 is very low, Kostis paper
    p[25] = 0.175 # Beta
    p[26] = 0 # delta_th
    p[27] = 0.1099 # q_nor
    p[28] = 5 # q_ach
    p[29] = 1.12 # K_nor
    p[30] = 0.65 # K_ach
    p[31] = 0.75 # Gamma
    p[32] = 58.6 # alpha_s0
    p[33] = 76.019 # alpha_p0
    y[0] = 0.2165 #0.2042 # eps1 ## initial values adapted after comparison with openCell simulation
    y[1] = 0.14369 #0.183 # eps2
    y[2] = 0.1128275 #0.161 # eps3
    p[34] = 0.01 # eps_wall - the strain that comes as input to the system
    y[3] = 2.407 #1.441 # c_nor
    y[4] = 1.95 #1.0 # c_ach
    y[5] = 71.205 #0 # delta_HR_s
    y[6] = 13.24 # delta_HR_pslow
    p[35] = p[23]-p[22] # delta_HR_smax
    p[36] = p[22]-p[24] # delta_HR_pmax
    return y, p

def computeRates(t, y, p):
    ydot = zeros(sizeStates)
    alg = zeros(sizeAlgebraic)
    alg = rootfind_0(t, p, y, alg)
    alg[1] = (p[35]*(power(y[3], 2.00000)))/(power(p[29], 2.00000)+power(y[3], 2.00000))
    ydot[5] = (-y[5]+alg[1])/p[20]
    alg[2] = (p[36]*(power(y[4], 2.00000)))/(power(p[30], 2.00000)+power(y[4], 2.00000))
    ydot[6] = (-y[6]+(1.00000-p[31])*alg[2])/p[21]
    alg[0] = p[34]-y[0]
    alg[3] = p[0]*(alg[0]-p[1]*p[26])
    alg[5] = p[15]*alg[3]
    alg[7] = p[13]+(p[11]-p[13])/(exp(p[16]*(alg[5]-p[32]))+1.00000)
    ydot[3] = -(y[3]/p[18])+p[27]*alg[7]
    alg[8] = p[14]+(p[12]-p[14])/(exp(-p[17]*(alg[5]-p[33]))+1.00000)
    ydot[4] = -(y[4]/p[19])+p[28]*alg[8]
    return ydot

def computeAlgebraic(p, y, t):
    alg = zeros(sizeAlgebraic)
    alg = rootfind_0(t, p, y, alg)
    alg[1] = (p[35]*(power(y[3], 2.00000)))/(power(p[29], 2.00000)+power(y[3], 2.00000))
    alg[2] = (p[36]*(power(y[4], 2.00000)))/(power(p[30], 2.00000)+power(y[4], 2.00000))
    alg[0] = -y[0]
    alg[3] = p[0]*(alg[0]-p[1]*p[26])
    alg[5] = p[15]*alg[3]
    alg[7] = p[13]+(p[11]-p[13])/(exp(p[16]*(alg[5]-p[32]))+1.00000)
    alg[8] = p[14]+(p[12]-p[14])/(exp(-p[17]*(alg[5]-p[33]))+1.00000)
    alg[4] = p[31]*alg[2]
    alg[6] = alg[4]+y[6]
    alg[9] = p[22]+y[5]
    alg[10] = p[22]-alg[6]
    alg[11] = alg[10]+((alg[9]-p[22])*(alg[10]-p[25]*p[24]))/(p[22]-p[25]*p[24])
    alg[12] = 60.0000/alg[11]
    return alg

initialGuess0 = None
def rootfind_0(t, p, y, alg):
    """Calculate values of algebraic variables for DAE"""
    global initialGuess0
    if initialGuess0 is None:
        initialGuess0 = ones(3)*0.1
    soln = fsolve(residualSN_0, initialGuess0, args=(alg, t, p, y), xtol=1E-6)
    initialGuess0 = soln
    ydot[0] = soln[0]
    ydot[1] = soln[1]
    ydot[2] = soln[2]
    return alg

def residualSN_0(algebraicCandidate, alg, t, p, y):
    """Python callback for fsolve()."""
    resid = zeros(3)
    ydot[0] = algebraicCandidate[0]
    ydot[1] = algebraicCandidate[1]
    ydot[2] = algebraicCandidate[2]
    resid[0] = (ydot[0]-((p[3]*(p[34]-y[0])-p[4]*(y[0]-y[1]))/p[8]+ydot[1]))
    resid[1] = (ydot[1]-((p[4]*(y[0]-y[1])-p[5]*(y[1]-y[2]))+p[8]*ydot[0]+p[9]*ydot[2])/(p[8]+p[9]))
    resid[2] = (ydot[2]-((p[5]*(y[1]-y[2])-p[6]*y[2])+p[9]*ydot[1])/(p[9]+p[10]))
    return resid

def solve_model():
    """Solve model with ODE solver"""
    from scipy.integrate import ode
    # Initialise constants and state variables
    (init_states, constants) = initConsts()

    # Set timespan to solve over
    voi = linspace(0, 10, 500)

    # Construct ODE object to solve
    r = ode(computeRates)
    r.set_integrator('vode', method='bdf', atol=1e-06, rtol=1e-06, max_step=1)
    r.set_initial_value(init_states, voi[0])
    r.set_f_params(constants)

    # Solve model
    states = zeros((len(voi), sizeStates))
    algebraic = zeros((len(voi), sizeAlgebraic))
    states[0] = init_states
    for i, t in enumerate(voi[1:]):
        if r.successful():
            r.integrate(t)
            states[i + 1] = r.y
        else:
            break

    # Compute algebraic variables
    for i, (s, v) in enumerate(zip(states, voi)):
        algebraic[i] = computeAlgebraic(constants, s, v)
    return (voi, states, algebraic)

def plot_model(voi, states, algebraic):
    """Plot variables against variable of integration"""
    import matplotlib.pyplot as plt
    (legend_states, legend_algebraic, legend_voi, legend_constants) = createLegends()
    plt.figure()
    plt.plot(voi, states)
    plt.plot(voi, algebraic)
    plt.xlabel(legend_voi)
    plt.legend(legend_states + legend_algebraic, loc='best')
    plt.show()

### BEGIN added for cgptoolbox

# @todo: The following module-level variables are shared across instances.
#        It might be better to wrap them in a class, allowing each instance of 
#        the same model to have its own parameter vector.

import sys
import numpy as np

ftype = np.float64 # explicit type declaration, can be used with cython
y0 = np.zeros(sizeStates, dtype=ftype)
ydot = np.zeros(sizeStates, dtype=ftype)
p = np.zeros(sizeConstants, dtype=ftype)
algebraic = alg = np.zeros(sizeAlgebraic, dtype=ftype)

y0[:], p[:] = initConsts()

# Sundials calling convention: https://computation.llnl.gov/casc/sundials/documentation/cv_guide/node6.html#SECTION00661000000000000000

def ode(t, y, ydot, f_data):
    """
    Compute rates of change for differential equation model.
    
    Rates are written into ydot[:]. 
    f_data is ignored, but required by the CVODE interface.
    
    The function returns 0 on success and -1 on failure.
    
    >>> ode(None, None, None, None)
    -1
    
    For debugging in case of failure, exception info is stored in the 
    module-level variable exc_info. (The message ends in "unsubscriptable" 
    under Python 2.6 but "not subscriptable" under Python 2.7, hence the 
    ellipsis.) Unfortunately, this is currently not implemented in a compiled 
    ODE. It will check the type of arguments before executing, but I am not 
    sure what happens in case of run-time errors inside the ODE.
    
    >>> exc_info
    (<type 'exceptions.TypeError'>,
    TypeError("'NoneType' object is ...subscriptable",),
    <traceback object at 0x...>)
    """
    global traceback
    traceback = None
    try:
        ydot[:] = computeRates(t, y, p)
        return 0
    except StandardError:
        import traceback
        ode.traceback = traceback.format_exc()
        return -1

def rates_and_algebraic(t, y):
    """
    Compute rates and algebraic variables for a given state trajectory.
    
    Unfortunately, the CVODE machinery does not offer a way to return rates and 
    algebraic variables during integration. This function re-computes the rates 
    and algebraics at each time step for the given state.
    
    This returns a simple float array; 
    :meth:`cgp.physmod.cellmlmodel.Cellmlmodel.rates_and_algebraic`
    will cast them to structured arrays with named fields.
    
    This version is pure Python; 
    :func:`~cgp.physmod.cythonize.cythonize`
    will generate a faster version.
    """
    t = np.atleast_1d(t)
    imax = len(t)
    # y can be NVector, unstructured or structured Numpy array.
    # If y is NVector, its data will get copied into a Numpy array.
    y = np.array(y).view(float)
    ydot = np.zeros_like(y)
    a = np.zeros((imax, len(alg)))
    for i in range(imax):
        ydot[i] = computeRates(t[i], y[i], p)
        if len(alg):
            # need np.atleast_1d() because computeAlgebraic() uses len(t)
            a[i] = computeAlgebraic(p, y[i], np.atleast_1d(t[i])).squeeze()
    return ydot, a

### END added for cgptoolbox

def solver2(timeArray,initial_states,constants):
    """
    Solve model with ODE solver
    solver function defined for the use with STARFiSh
    """
    
    from scipy.integrate import ode
    # Initialise constants and state variables
    #(init_states, constants) = initConsts()

    # Set timespan to solve over
    voi = timeArray
    
    # Construct ODE object to solve
    r = ode(computeRates)
    r.set_integrator('vode', method='bdf', atol=1e-06, rtol=1e-06, max_step=1)
    r.set_initial_value(initial_states, voi[0])
    r.set_f_params(constants)

    # Solve model
    states = zeros((len(voi), sizeStates))
    algebraic = zeros((len(voi), sizeAlgebraic))
    states[0] = initial_states
    for i, t in enumerate(voi[1:]):
        if r.successful():
            r.integrate(t)
            states[i + 1] = r.y
        else:
            break

    # Compute algebraic variables
    for i, (s, v) in enumerate(zip(states, voi)):
        algebraic[i] = computeAlgebraic(constants, s, v)
    return (voi, states, algebraic)



if __name__ == "__main__":
    
    
    (states, constants) = initConsts()
    timeArray = linspace(0, 10, 500) #second value determined by flow simulation time step? number of intervals determined by timestep for ODE/DAE solving?
    strain = 0.0100000+0.00500000*sin(timeArray)
    timeArray2 = linspace(0,0.02,2)
    p[34] = strain[0]
    print p[34]
    voi, states, algebraic = solver2(timeArray2,states,constants)
    print algebraic[-1][11]
    
    HR = np.zeros(np.size(strain))
    HR[0] = algebraic[-1][11]
    
    for t in xrange((size(strain)-1)):
        
        p[34] = strain[t+1]
        voi, states, algebraic = solver2(timeArray2,states[-1],constants)
        #print size(algebraic)    
        print p[34]
        print algebraic[-1][11]
        HR[t+1] = algebraic[-1][11]
        
    import matplotlib.pyplot as plt
    plt.figure()
    plt.plot(timeArray, HR)
    #plt.plot(timeArray, strain)
    plt.show()
    

        
    
    #t, y, algebraic = solve_model()
    #plot_model(t, y, algebraic)


