import numpy as np

import sys,os
from classBoundaryConditions import VaryingElastance, Valve
from classVascularNetwork import VascularNetwork

# set the path relative to THIS file not the executing file!
cur = os.path.dirname( os.path.realpath( __file__ ) )
sys.path.append(cur+'/NetworkLib')

from classBoundarys import Boundary

from classSystemEquations import *
from classConnections import *
from classFields import *
#from classCommunicators import *
from classBaroreceptor import *
from classVenousPool import *
from classDataHandler import DataHandler
from classTimer import *

sys.path.append(cur+'/UtilityLib/')
from processing import memoryUsagePsutil

import pprint 
from copy import copy as copy
import gc

class FlowSolver(object):

    
    def __init__(self,vascularNetwork, quiet=False):
        '''
        Constructor       
        '''
                
        if vascularNetwork == None: print "ERROR: No vascularNetwork given!" / exit()
        assert isinstance(vascularNetwork, VascularNetwork)
        # the vascular network to solve
        self.vascularNetwork = vascularNetwork
        self.vascularNetwork.quiet = quiet
        
        self.vessels = self.vascularNetwork.vessels
        self.fields = {}
        # the boundarys of the network { vesselID : [<instance>::classBoundary_02(Characteristics.py), .. ]}
        # 1 boundary for each start/end-vessel except if only 1 vessel in the network
        self.boundarys = {}
        # the system Equations of each vessel { vesselID : <instance>::classSystemEquations(SystemEquations) }
        self.systemEquations = {}
        # the connections of the Network { motherVesselID : <instance>::classConnections, ...}
        self.connections  = {}                
        # the communicator objects of the vascularNetwork {communicatorID : <instance>::classCommunicator}
        self.communicators = {}
        
        self.timers = {}
        timers = False
        if timers == True:
            self.timers = {'0':{'type':'valsalva','Tstart': 5, 'Tend': 7, 'deltaP':-300*133.32, 'vesselID': [1,2,3,4,7,14,18,19,21,27]}}
              
        # Baroreceptor model
        # this needs to be configured by the xml specification, as it breaks the other networks if
        # you assume these static IDs will be present for all simulations.
        self.baroreceptors = {}
        # Set this to False for checkins unless the test cases work with it.
        baro = True
        if baro == True:
            print "\n WARNING doing baroreseptor!"
            print " self.baroreceptors = {'0': {'cellMLBaroreceptorModel': True, 'vesselId':[2,14], 'receptorType':'AorticBR', 'modelName':'bugenhagenAorticBR'}}"
            print "\n"
            self.baroreceptors = {'0': {'cellMLBaroreceptorModel': True, 'vesselId':[2,14], 'receptorType':'AorticBR', 'modelName':'bugenhagenAorticBR'}}
           
            #self.baroreceptors = {'0':{'receptorType':'CarotidBR','vesselIdLeft':12,'vesselIdRight':16,'cellMLBaroreceptorModel': False, 'modelName': 'Ursino'}}
             
        vein = True
        self.venousPool = 0
        #
        
        # list of numerical objects (field,connection,boundary objects as in the traversing list)
        self.numericalObjects = []
        # time step
        self.dt = None
        # number of Timesteps
        self.nTsteps = None     
        
        # total Simulation time
        self.totalTime = None
    
        # timestep Counter
        self.currentTimeStep = [0]
        
        self.cycleMode = False
        
        # Initialize idices to track where in memory the current solution is stored
        self.memoryOffset = [0]
        self.currentMemoryIndex = [0]
        
        # Set div output 
        self.output = {}
        
        self.simplifyEigenvalues = self.vascularNetwork.simplifyEigenvalues
        
        self.riemannInvariantUnitBase = self.vascularNetwork.riemannInvariantUnitBase
        
        self.solvingSchemeConnections = self.vascularNetwork.solvingSchemeConnections
       
        # bool for cfl meshing with automatic grid adaption
        self.automaticGridAdaptation = self.vascularNetwork.automaticGridAdaptation
        
        # rigidAreas True: A = A0 False: A = A(P)
        self.rigidAreas = self.vascularNetwork.rigidAreas
        
#         # Define the output of A, depending on the characteristic system 0.1
#         if self.rigidArea == '02':
#             self.AFunction = self.AFunctionSys0
#         elif self.rigidArea == '2': 
#             self.AFunction = self.AFunctionSys1

#         self.solvingScheme = self.vascularNetwork.networkSolver['solvingScheme'] 
#         if self.solvingScheme == 'MacCormack':
#             self.solve = self.MacCormack  
#         elif self.solvingScheme == 'MacCormack_Field': 
#             self.solve = self.MacCormack_Field
        
        #define solve function
        self.solve = self.MacCormack_Field
                
        # initialize system
        self.vascularNetwork.initialize(initializeForSimulation = True)
        
        self.initializeTimeVariables(quiet)
        
        self.initializeSolutionMatrices() # init data in vessels
        
        self.initializeSystemEquations()
        self.initializeBoundarys()
        self.initializeConnections()
        self.initializeFields()
        self.initializeCommunicators()
        if vein == True:
            self.initializeVenousPool()
        
        self.initializeBaroreceptors()
        self.initializeTimers()
        self.initializeNumericalObjectList()
        if quiet==False:
            self.initOutput() # feedback
        self.quiet = quiet 
       
        

    '''       
    ########################################################################################
    # initialisation Methods
    ########################################################################################
    '''
        
    
    def calcTimeStep(self,dz,c,CFL):
        return (CFL*dz)/c

    def initializeTimeVariables(self, quiet):
        '''
        initialize time variable dt and Tstep
        '''
        self.totalTime = self.vascularNetwork.totalTime
                
        initialValues = self.vascularNetwork.initialValues
        
        dt_min,dz_min,c_max,gridNodens = [],[],[],[]
        #create waveSpeed Log file
        logfileData = {}
        
        dt = self.totalTime
        for vessel in self.vessels.itervalues():
        # Calculate time variables
            #estimate initial pressure
            p0,p1 = initialValues[vessel.Id]['Pressure']
            
            initialPressure = np.linspace(p0,p1,vessel.N) 
            
            A0_max = max(vessel.A(initialPressure))
            #c_high = vessel.c(A0_max,vessel.initialPressure)
            
            #c_high1 = vessel.c(A0_max,0)
            Compliance = vessel.C(initialPressure)
            c_high = vessel.c(A0_max, Compliance)
            
            dz_low = min(vessel.dz)
            dt = self.calcTimeStep(dz_low,c_high,self.vascularNetwork.CFL) 
            c_max = np.append(c_max,c_high)
            dt_min = np.append(dt_min,dt)
            dz_min = np.append(dz_min,dz_low)
            gridNodens = np.append(gridNodens,vessel.N)
            
            logfileData[vessel.Id] = [max(c_high),min(c_high),min(dt),vessel.dz,vessel.N]
            
        # Set time variables 
        self.dt = min(dt_min)
        # calculate time steps
        self.nTsteps = int(np.ceil(self.totalTime/self.dt))
        # calculate time steps for initialisation phase
        nTstepsInitPhase = 0
        if self.vascularNetwork.initialisationPhaseExist:
            initPhaseTimeSpan = self.vascularNetwork.initPhaseTimeSpan
            nTstepsInitPhase = int(np.ceil(initPhaseTimeSpan/self.dt))
        # correct time steps
        self.nTsteps += nTstepsInitPhase
            
        # update vascular network variables
        self.vascularNetwork.update({'dt':self.dt,
                                     'nTsteps': self.nTsteps,
                                     'nTstepsInitPhase': nTstepsInitPhase})
                    
        self.output['dz_min']     = min(dz_min)
        self.output['c_min']      = min(c_max)
        self.output['c_max']      = max(c_max)
        self.output['gridNodens'] = sum(gridNodens)
        
        self.output['CFLcorrect'] = []
                
        ###########
        #### grid correction methods
        
        automaticGridCorrection = {}
        
        logfile = open(str(cur+'/../'+'LOGcurrentWaveSpeed.txt'),'wb')
        logfile2 = open(str(cur+'/../'+'LOGproposedGrid.txt'),'wb')
        CFL = self.vascularNetwork.CFL
        for vesselT,data in logfileData.iteritems():
            #number of deltaX
            Nnew = int((sum(data[3])*CFL/(self.dt*data[0])))
            
            L = sum(data[3])
            #calculate number of dx: M = L/dx
            Mnew = int(L*CFL/self.dt/data[0])
                        
            dz_new = L/Mnew
            dt_new = self.calcTimeStep(dz_new,data[0],CFL)
            
            while dt_new < self.dt:
                Mnew = Mnew-1
                dz_new = L/Mnew
                dt_new = self.calcTimeStep(dz_new,data[0],CFL)
            
            # calculate gridpoints N = N+1
            Nnew = Mnew+1
            if Nnew == data[4]: 
                logfile.write(''.join(['vessel ',str(vesselT), ' c_max: %2.3f'%(data[0]),'   dt (ms) %2.6f'%(data[2]*1.0E3),' | res CFL: %2.3f'%(data[0]*self.dt/min(data[3])),' || already best N', '\n']))
                #self.output['CFLcorrect'].append(' '.join([str(vesselT).rjust(2).ljust(15),' no correction']))
            else: 
                logfile.write(''.join(['vessel ',str(vesselT), ' c_max: %2.3f'%(data[0]),'   dt (ms) %2.6f'%(data[2]*1.0E3),' | res CFL: %2.3f'%(data[0]*self.dt/min(data[3])),' || prop: N%2.0f'%Nnew,'    dN %.0f'%(Nnew-data[4]),'    dtNew %.4f'%(dt_new*1.e3),'   CFL: %2.3f'%(data[0]*self.dt/dz_new), '\n']))
                self.output['CFLcorrect'].append(' '.join([str(vesselT).ljust(3),'|',str(int(data[4])).ljust(3),'->',str(Nnew).ljust(3),'|', '%2.3f'%(data[0]*self.dt/min(data[3])),'->', '%2.3f'%(data[0]*self.dt/dz_new),'|']))
                automaticGridCorrection[vesselT] = Nnew
            logfile2.write(''.join([str(int(Nnew)),'\n']))
        logfile.close()
        logfile2.close()    
                
        if self.output['CFLcorrect'] != []:
            if quiet == False:
                print '====================================='
                print '___CFL-correction: grid adaptation___'
                print 'Id  | gridPoints |       CFL      |'
                print '    | now -> new |   now -> new   |'
                for CFLcorr in self.output['CFLcorrect']:
                    print '%s' % (CFLcorr)
                
            if automaticGridCorrection != {}:
                gridCorrection = 'ohYesDoItPlease'
                if self.automaticGridAdaptation == True: gridCorrection = 'y'
                while  gridCorrection not in (' ','','y','Y','n','N'): 
                    gridCorrection = raw_input('Do you whish to adapt grid? (yes [<ENTER>,<y>,<Y>]/no [<n>,<N>])')
                
                if gridCorrection in (' ','','y','Y'):
                    #if quiet == False: print ' proceed with: grid aptation for vessels {} \n'.format(automaticGridCorrection.keys())
                    arrayN = 0
                    for vesselId,Nnew in automaticGridCorrection.iteritems():
                        self.vessels[vesselId].update({'N':Nnew})
                        self.vessels[vesselId].initialize({})
                        
                        newOutput = self.output['CFLcorrect'][arrayN].split(' no')[0]
                        self.output['CFLcorrect'][arrayN] = ' '.join([newOutput,'yes'])
                        arrayN = arrayN+1
        gridNodes = 0
        for vessel in self.vascularNetwork.vessels.itervalues():
            gridNodes += vessel.N 
            
        self.output['gridNodens'] = int(gridNodes)
        
                
    def initializeSolutionMatrices(self):
        '''
        initialize solution matrices --> moved to vascularNetwork
        '''
        # initialiase solution matrices, gravity and position over space
        self.vascularNetwork.initializeNetworkForSimulation()
        
        #exit()
                
#        initialValues = self.vascularNetwork.initialValues
#        
#         for vesselId,vessel in self.vessels.iteritems():
#             
#             # get init values from init phase
#             #Pinit = vessel.Psol[-1,:]
#             #Qinit = vessel.Qsol[-1,:]
#             #Ainit = vessel.Asol[-1,:]
#             
#             # create new arrays for simulations
#             vessel.Psol = np.ones((self.nTsteps,vessel.N))
#             vessel.Qsol = np.zeros((self.nTsteps,vessel.N))
#             vessel.Asol = np.zeros((self.nTsteps,vessel.N))
#             # apply initial values to arrays
#             try:
#                 p0,p1 = initialValues[vesselId]['Pressure']
#                 Qm    = initialValues[vesselId]['Flow']
#                 vessel.Psol[0] = np.linspace(p0,p1,vessel.N)   
#                 vessel.Qsol[0] = np.ones((1,vessel.N))*Qm  
#             except:
#                 print "Error: cFS could not use initial values from network"
#                 pass
#             
#             vessel.Asol[0] = np.ones((1,vessel.N))*vessel.A(self.vessels[vesselId].Psol[0])   
#                    
#             vessel.positionStart    = np.zeros((self.nTsteps,3))
#             vessel.positionEnd      = np.zeros((self.nTsteps,3))
#             vessel.rotToGlobalSys   = np.zeros((self.nTsteps,3,3))
#             vessel.netGravity       = np.zeros((self.nTsteps,1))
                       
#         ## initialse varying elastance model
#         for vesselId,boundaryConditions in self.vascularNetwork.boundaryConditions.iteritems():
#             for bC in boundaryConditions:
#                 if bC.name in ['VaryingElastanceHeart','VaryingElastanceSimple']:
#                     Qm    = initialValues[vesselId]['Flow']
#                     bC.update({'aorticFlowPreviousTimestep':Qm})
#                     bC.initializeSolutionVectors(self.nTsteps)
#                     
#         ## initialize gravity and 3d positions over time
#         # create motion decription out of motion dict of vascularNetwork
#         #self.motion = [] # [ { vesselId : { angleXMother: ax, angleYMother: ay, angleZMotheraz }_n ] for all n in range (0,nTsteps-1)
#         
#         # define motion
#         motionDict = {}
#         headUpTilt = False
#         ## head up tilt
#         if headUpTilt == True:
#             tSteps4 = int(self.nTsteps/6.0)
#             start = self.vessels[1].angleXMother
#             end   = start-80*np.pi/180
#             startAngle = np.ones(tSteps4*2.0)*start
#             endAngle   = np.ones(tSteps4)*end
#             tiltAngle  = np.linspace(start, end, self.nTsteps-3*tSteps4)
#              
#             angleXSystem = np.append(startAngle,np.append(tiltAngle,endAngle))
#                      
#             motionDict = {1:{'angleXMotherTime': angleXSystem}}
#          
#         for vesselId,angleDict in motionDict.iteritems():
#             self.vessels[vesselId].update(angleDict)
#             
#         ## calculate gravity and positions   
#         self.vascularNetwork.calculate3DpositionsAndGravity(nTsteps = self.nTsteps)
#             
#         ## calculate venous pressure for windkessel
#         self.vascularNetwork.initializeVenousGravityPressureTime(self.nTsteps)
                  
    def initializeSystemEquations(self):
        '''
        initialize system Equations
        '''
        for vesselId,vessel in self.vessels.iteritems():
            self.systemEquations[vesselId] = System(vessel,
                                                    self.simplifyEigenvalues,
                                                    self.riemannInvariantUnitBase,
                                                    self.currentTimeStep,
                                                    self.dt)
            # initialize system equations
            self.systemEquations[vesselId].updateSystem(self.vessels[vesselId].Psol[0],
                                                        self.vessels[vesselId].Qsol[0],
                                                        self.vessels[vesselId].Asol[0])
         
    def initializeBoundarys(self):
        '''
        initialize boundarys
        '''
        if len(self.vessels) == 1:
            rootId = self.vascularNetwork.root
            bcList0 = []
            bcList1 = []
            for bc in self.vascularNetwork.boundaryConditions[rootId]:
                if bc.position == 0:     bcList0.append(bc)
                elif bc.position == -1:  bcList1.append(bc)
            self.boundarys[rootId] = [Boundary( self.vessels[rootId],
                                                bcList0,
                                                self.rigidAreas,
                                                self.dt,
                                                self.currentMemoryIndex,
                                                self.currentTimeStep,
                                                self.nTsteps,
                                                self.systemEquations[rootId]),
                                      Boundary( self.vessels[rootId],
                                                bcList1,
                                                self.rigidAreas,
                                                self.dt,
                                                self.currentMemoryIndex,
                                                self.currentTimeStep,
                                                self.nTsteps,
                                                self.systemEquations[rootId])]
            self.output['BndrNR'] = 2
        else:
            for vesselId,boundaryConditions in self.vascularNetwork.boundaryConditions.iteritems():
                self.boundarys[vesselId] = [  Boundary( self.vessels[vesselId],
                                                        boundaryConditions,
                                                        self.rigidAreas,
                                                        self.dt,
                                                        self.currentMemoryIndex,
                                                        self.currentTimeStep,
                                                        self.nTsteps,
                                                        self.systemEquations[vesselId])]
                
            self.output['BndrNR'] = len(self.boundarys)
    
    def initializeConnections(self):
        '''
        initialize Connections of the network
        by traversing the network tree
        '''
        treeList = self.vascularNetwork.treeTraverseList
        
        for leftMother,rightMother,leftDaughter,rightDaughter  in self.vascularNetwork.treeTraverseConnections:  
            ## link
            if rightMother == None and rightDaughter == None:
                self.connections[leftMother] = Link(  self.vessels[leftMother],
                                                      self.systemEquations[leftMother],
                                                      self.vessels[leftDaughter],
                                                      self.systemEquations[leftDaughter],
                                                      self.currentMemoryIndex,
                                                      self.dt,
                                                      self.rigidAreas,
                                                      self.solvingSchemeConnections)
            ## bifurcation
            elif rightMother == None:
                self.connections[leftMother] = Bifurcation(  self.vessels[leftMother],
                                                             self.systemEquations[leftMother],
                                                             self.vessels[leftDaughter],
                                                             self.systemEquations[leftDaughter],
                                                             self.vessels[rightDaughter],
                                                             self.systemEquations[rightDaughter],
                                                             self.currentMemoryIndex,
                                                             self.dt,
                                                             self.rigidAreas,
                                                             self.solvingSchemeConnections)
            ## anastomosis
            elif rightDaughter == None:
                anastomosisId = leftMother
                if treeList.index(leftMother) > treeList.index(rightMother):
                    anastomosisId = rightMother
                self.connections[anastomosisId] = Anastomosis(self.vessels[leftMother],
                                                             self.systemEquations[leftMother],
                                                             self.vessels[rightMother],
                                                             self.systemEquations[rightMother],
                                                             self.vessels[leftDaughter],
                                                             self.systemEquations[leftDaughter],
                                                             self.currentMemoryIndex,
                                                             self.dt,
                                                             self.rigidAreas,
                                                             self.solvingSchemeConnections)
        
    def initializeFields(self):
        
        for vesselId,vessel in self.vessels.iteritems():    
            self.fields[vesselId] = Field(  vessel,
                                            self.currentMemoryIndex,
                                            self.dt, 
                                            self.systemEquations[vesselId],
                                            self.rigidAreas)
    

    def initializeBaroreceptors(self):
        
        '''
        method used to initialize Baroreceptor (baroreflex) objects
        '''
        
        for baroId, baroData in self.baroreceptors.iteritems():
            
            baroData['currentTimeStep']         = self.currentTimeStep
            baroData['currentMemoryIndex']      = self.currentMemoryIndex
            baroData['dt']                      = self.dt
            baroData['nTsteps']                 = self.nTsteps
            
            try:                
                bc2out = {}
                terminalBoundaries = 0
                
                for bcId,bcs in self.vascularNetwork.boundaryConditions.iteritems():
                    
                    if bcId == self.vascularNetwork.root:
                        
                        for bc in bcs:
                            if bc.type == 1:
                                baroData['boundaryCondition'] = bc
                            
                            elif bc.type == 2:
                                baroData['boundaryConditionII'] = bc
        
                            else:
                                print "ERROR FS 525: Wrong type of boundary condition"   
                
                    elif bcId != self.vascularNetwork.root:
                        #print "FS 499"
                        for bc in bcs:
                            if bc.type == 2: # type 2 BC, outflow or Varying Elastance heart
                                bc2out[bcId] = bc
                                terminalBoundaries = terminalBoundaries + 1
                
                baroData['boundaryConditionIIout'] = bc2out
                                                                       
            except: pass
            
             
            #for an aortic baroreceptor
            #usually the aortic arch is modelled with two vessel segments (Aortic Arch A and Aortic Arch B)
            # therefore it takes two vessels with their respective vesselID's
                       
            if baroData['receptorType'] == 'AorticBR':
                
                A1 = self.vessels[baroData['vesselId'][0]].Asol
                A2 = self.vessels[baroData['vesselId'][1]].Asol
                P1 = self.vessels[baroData['vesselId'][0]].Psol
                P2 = self.vessels[baroData['vesselId'][1]].Psol
                
                baroData['Area1'] = A1
                baroData['Area2'] = A2
                baroData['Pressure1'] = P1
                baroData['Pressure2'] = P2
                baroData['Strain'] = np.zeros([self.nTsteps,np.shape(A1)[1]+np.shape(A2)[1]])
                baroData['MStrain'] = np.zeros(self.nTsteps)
                baroData['T']       = np.zeros(self.nTsteps)
                
                #baroData['initialCompliance1'] = self.vessels[baroData['vesselId'][0]].compliance
                #baroData['initialCompliance2'] = self.vessels[baroData['vesselId'][1]].compliance
                
                self.baroreceptors[baroId] = AorticBaroreceptor(baroData) # call the constructor
                
            
            ## usually the left and right carotid sinus are modelled with one vessel each
            ## therefore the CarotidBR takes two Vessel Id's one for the left CS and one for the right CS        
            elif baroData['receptorType'] == 'CarotidBR':
                
                baroData['pressureLeft']   = self.vessels[baroData['vesselIdLeft']].Psol
                baroData['pressureRight']  = self.vessels[baroData['vesselIdRight']].Psol
                baroData['LeftAfferentSignal'] = np.zeros(np.shape(self.vessels[baroData['vesselIdLeft']].Psol))
                baroData['RightAfferentSignal']= np.zeros(np.shape(self.vessels[baroData['vesselIdLeft']].Psol))
                baroData['AfferentSignal'] = np.zeros(np.shape(self.vessels[baroData['vesselIdLeft']].Psol))
                baroData['EfferentSignal'] = np.zeros(np.shape(self.vessels[baroData['vesselIdLeft']].Psol))
                baroData['AffectedValue']  = np.zeros(np.shape(self.vessels[baroData['vesselIdLeft']].Psol))

                baroData['terminalBoundaries'] = terminalBoundaries # number of terminal boundaries used to calculate delta_R for each WK at the distal end of a network
                baroData['VenousPool'] = self.venousPool # venous pool object for the update of Vusv
                
                self.baroreceptors[baroId] = CarotidBaroreceptor(baroData) # call the constructor
                
            else:
                print 'Error: invalid Baroreceptor type'
    
        
    def initializeVenousPool(self):
        """
        method for the initialization of a "venous pool"
        """
        
        VPdict = {}
        VPdict['currentTimeStep'] = self.currentTimeStep
        VPdict['currentMemoryIndex'] = self.currentMemoryIndex
        VPdict['dt'] = self.dt
        VPdict['nTsteps'] = self.nTsteps
        VPdict['boundarys'] = self.boundarys
        
        self.venousPool = venousPool(VPdict) # call to the constructor of venousPool
        
    
    def initializeTimers(self):
        
        '''
        method used to initialize Timer objects
        '''
        for TimerId, TimerData in self.timers.iteritems():
            
            TimerData['currentTimeStep']         = self.currentTimeStep
            TimerData['currentMemoryIndex']      = self.currentMemoryIndex
            TimerData['dt']                      = self.dt
            TimerData['nTsteps']                 = self.nTsteps
            
            
            if TimerData['type'] == 'valsalva':
                
                TimerData['VesselsToModify']     = {}
                
                for i in TimerData['vesselID']:
                    
                    TimerData['VesselsToModify'][i] = self.vessels[i]
                
                
                self.timers[TimerId] = Valsalva(TimerData)
                
            else: pass
    
    
            
    
    def initializeCommunicators(self):
        
        
        #print 'cFS 435 Communicators',self.vascularNetwork.communicators
        for comId, comData in self.vascularNetwork.communicators.iteritems():
        #for comId, comData in self.communicators.iteritems():      
            #try:
            data = {'Pressure': self.vessels[comData['vesselId']].Psol,
                    'Flow'    : self.vessels[comData['vesselId']].Qsol,
                    'Area'    : self.vessels[comData['vesselId']].Asol
                    }
            comData['data']           = data
                
                
            #except: pass
            
            ## not used now
#             ## for visualisation                                        
#             if 'bloodVolume' in comData['quantitiesToPlot']:
#                 for boundary in self.boundarys[vesselId]:
#                     try: comData['data']['bloodVolume'].append(boundary.BloodVolumen)
#                     except: comData['data']['bloodVolume'] = [boundary.BloodVolumen]
#             
            
            ## for baroreceptor
            try:            
                for bcId,bcs in self.vascularNetwork.boundaryConditions.iteritems():
                    if bcId == comData['vesselId']:
                        for bc in bcs:
                            if bc.type == 1:
                                comData['boundaryCondition'] = bc                                                            
            except: pass
                        
            comData['currentMemoryIndex'] = self.currentMemoryIndex
            comData['currentTimeStep']    = self.currentTimeStep
            comData['dt']                 = self.dt
            
            self.communicators[comId] = eval(comData['comType'])(comData) # call the constructor
            
              
    def initializeNumericalObjectList(self):
        '''
        ## fill numObjectList (self.currentTimeStepumericalObjects) traversing the treeList 
        # 1. add root boundary
        # 2  add vessels
        # 3  add connection or distal boundary condition
        # 4. repeat 2,3 for the hole tree 
        # 5. add communicators
        # 6. add blocking Wait if multiprocessing
        '''
        
        # get treetraversing list
        treeList = self.vascularNetwork.treeTraverseList
        
        singleVesselNetwork = False
        if len(self.vessels) == 1:
            singleVesselNetwork = True
        
        for vesselId in treeList:
            int(vesselId)
            ## check if root add BC
            try:
                if vesselId == self.vascularNetwork.root:
                    self.numericalObjects.append(self.boundarys[vesselId][0])
            except: pass
            
            ## add field
            self.numericalObjects.append(self.fields[vesselId])
            
            ## try add Connection
            try: self.numericalObjects.append(self.connections[vesselId])    
            except: pass
            
            ## try add distal BC
            try:
                if vesselId in self.vascularNetwork.boundaryVessels:
                    if singleVesselNetwork == False:
                        self.numericalObjects.append(self.boundarys[vesselId][0])
                    else:
                        self.numericalObjects.append(self.boundarys[vesselId][1])
            except: pass
        
        for communicator in self.communicators.itervalues():
            self.numericalObjects.append(communicator) 
            try:    communicator.startRealTimeVisualisation()
            except: pass
            
        for baroreceptor in self.baroreceptors.itervalues():
            self.numericalObjects.append(baroreceptor)
            
        for timer in self.timers.itervalues():
            self.numericalObjects.append(timer)
                   
        if self.venousPool != 0:
            self.numericalObjects.append(self.venousPool)
        else: pass
            
        dataHandler = DataHandler(self.currentTimeStep,
                                  self.nTsteps,
                                  self.vessels,
                                  self.currentMemoryIndex,
                                  self.vascularNetwork.memoryArraySizeTime)
        
        self.numericalObjects.append(dataHandler)
        
        self.memoryOffset = dataHandler.memoryOffset
                                   
    def initOutput(self):
        '''
        initialize solution matrices
        '''
        #print '====================================='
        print '___________Time variables ___________'
        print '%-20s %2.3f' % ('totaltime (sec)',self.totalTime)
        print '%-20s %2.3f' % ('dt (ms)',self.dt*1.0E3)
        print '%-20s %4d' % ('nTsteps',self.nTsteps)
        print '___________Div variables ____________'
        print '%-20s %2.1f' % ('Q init (ml s-1)',self.vascularNetwork.initialValues[self.vascularNetwork.root]['Flow']*1.e6)
        print '%-20s %2.1f' % ('P init (mmHg)',self.vascularNetwork.initialValues[self.vascularNetwork.root]['Pressure'][0]/133.32)
        try: print '%-20s %2.1f' % ('R_cum (mmHg s ml-1)',self.vascularNetwork.Rcum[self.vascularNetwork.root]/133.32*1.e-6)
        except: pass
        print '%-20s %2.1f' % ('CFL init max',self.vascularNetwork.CFL)
        print '%-20s %2.1f' % ('dz min (mm)',self.output['dz_min']*1.0E3)
        print '%-20s %2.1f' % ('c min (m/s)',self.output['c_min'])
        print '%-20s %2.1f' % ('c max (m/s)',self.output['c_max'])
        print '%-20s %4d' % ('Grid nodens',self.output['gridNodens'])
        print '___________Num variables ____________'
        print '%-20s %4d' % ('NumObj',len(self.fields)+len(self.boundarys)+len(self.connections))
        print '%-20s %4d' % ('NumFields',len(self.fields))
        print '%-20s %4d' % ('NumConnections',len(self.connections))
        print '%-20s %4d' % ('NumBoundarys',len(self.boundarys))
        print '%-20s %4d' % ('NumCommunicators',len(self.communicators))
        print '%-20s %4d' % ('NumBaroreceptors',len(self.baroreceptors))
        print '%-20s %4d' % ('NumObj calls',len(self.numericalObjects)*self.nTsteps)               
        print '%-20s %4d' % ('used Memory (Mb)',memoryUsagePsutil()  )
        #print self.communicators['0']
        #print np.shape(self.communicators['0'].data['Strain'])
        #print np.shape(self.communicators['0'].data['MStrain'])
        print '===================================== \n'
        
            
    '''
    ########################################################################################
    # Solver Methods:
    #
    #    MacCormack_Field
    #     ##MacCormack <- no in use anymore
    #    
    #
    ########################################################################################
    '''
       
    def MacCormack_Field(self):
        '''
        MacCormack solver method with forward-euler time steping,
        Using either Characteristic system 0 or 1 as defined in the XML-file.
        
        This method is solving the system by looping through the defined network
        imposing the boundary conditions based on Riemann Invariants and then solving the vessels, 
        conncetions, bifucations with a predictor-corrector step method
        '''
        print "Solving system ..."
        
        reflectionCoefficientCount = 0
        maxRef = 0
               
        if self.cycleMode == False:
            # original
                       
            for n in xrange(self.nTsteps):
                self.currentTimeStep[0] = n
                self.currentMemoryIndex[0] = n - self.memoryOffset[0]
                #[no() for no in self.numericalObjects]
                for numericalObject in self.numericalObjects:
                    numericalObject()
                
        ## to be concentrated with original cycle mode !!
        else:
            # steady state variables
            P_lastCycle  = {}
            Q_lastCycle  = {}
            A_lastCycle  = {}
            
            for vesselId,vessel in self.vessels.iteritems():
            
                initialValues = self.vascularNetwork.initialValues
                p0,p1 = initialValues[vesselId]['Pressure']
                Qm    = initialValues[vesselId]['Flow']
                
                P_lastCycle[vesselId]  = np.ones((self.nTsteps,vessel.N))
                Q_lastCycle[vesselId]  = np.ones((self.nTsteps,vessel.N))
                A_lastCycle[vesselId]  = np.ones((self.nTsteps,vessel.N))
                
            
            for cycle in xrange(self.numberCycles-1):
                print ' solving cycle {}'.format(cycle+1)
                # 1. solve cycle
                for n in xrange(self.nTsteps-1):
                    
                    self.currentTimeStep[0] = n
                    for numericalObject in self.numericalObjects:
                        numericalObject()
                # 2. check for steady state
                if self.quiet == False:
                    for vesselId in self.vessels.keys():
                        #Perror =  np.sum(np.sqrt((np.divide((P_lastCycle[vesselId]-self.P[vesselId]),P_lastCycle[vesselId]))**2.0))/self.P[vesselId].size
                        #Qerror =  np.sum(np.sqrt((np.divide((Q_lastCycle[vesselId]-self.Q[vesselId]),Q_lastCycle[vesselId]))**2.0))/self.Q[vesselId].size
                        #Aerror =  np.sum(np.sqrt((np.divide((A_lastCycle[vesselId]-self.A[vesselId]),A_lastCycle[vesselId]))**2.0))/self.A[vesselId].size
                         
                        Perror =  np.max(np.sqrt((np.divide((P_lastCycle[vesselId]-self.P[vesselId]),P_lastCycle[vesselId]))**2.0))
                        #Qerror =  np.max(np.sqrt((np.divide((Q_lastCycle[vesselId]-self.Q[vesselId]),Q_lastCycle[vesselId]))**2.0))
                        Aerror =  np.max(np.sqrt((np.divide((A_lastCycle[vesselId]-self.A[vesselId]),A_lastCycle[vesselId]))**2.0))
                         
                         
                        P_lastCycle[vesselId] = self.P[vesselId].copy()
                        #Q_lastCycle[vesselId] = self.Q[vesselId].copy()
                        A_lastCycle[vesselId] = self.A[vesselId].copy()
                        print '{} {}'.format(Perror, Aerror)
                
                # 3. rehash solution arrays if not last cycle
                if cycle is not self.numberCycles-1:
                    for vesselId in self.vessels.keys():
                
                        self.P[vesselId][0]    = self.P[vesselId][-1]
                        self.Q[vesselId][0]    = self.Q[vesselId][-1]
                        self.A[vesselId][0]    = self.A[vesselId][-1]
                        


#             for bif in self.vascularNetwork.treeTraversingGenerationBifurcation:
#             
#                 motherID = bif[0]
#                 leftDaughter = bif[1]
#                 rightDaughter = bif[2]
#                 
#                 # mother self.vessels[motherID]
#                 impedanceM = self.vessels[motherID].Impedance(self.P[motherID][n])
#                 AdmittanceM = 1.0/impedanceM[-1]
#                 
#                 # left daughter self.vessels[leftDaughter]
#                 impedanceLD = self.vessels[leftDaughter].Impedance(self.P[leftDaughter][n])
#                 AdmittanceD = 1.0/impedanceLD[0]
#                 #print  AdmittanceD
#                 
#                 try:
#                     #right daugther  self.vessels[rightDaughter]
#                     impedanceRD = self.vessels[rightDaughter].Impedance(self.P[rightDaughter][n])
#                     AdmittanceD = AdmittanceD+1.0/impedanceRD[0]
#                 
#                 except: pass
#                 
#                 expectedReflection = 0.5
#                 ReflectionCoeffBif = (AdmittanceM-AdmittanceD) / (AdmittanceM+AdmittanceD)
#                 if ReflectionCoeffBif != expectedReflection:
#                     reflectionCoefficientCount = reflectionCoefficientCount+1
#                     reflectionError = abs(ReflectionCoeffBif-expectedReflection)/expectedReflection
#                     if  reflectionError > maxRef:
#                         maxRef = reflectionError
#                     #print 'bifurcation', bif,' n ',n ,' Ref ',ReflectionCoeffBif, maxRef, ' count ',reflectionCoefficientCount 
#                     #raw_input()
        
#         ## Checks if VaryingElastance is used as the boundary condition at the root of the network, and if so 
#         ## returns various data from the ventricle as well as aortic and mitral valves
#         if not np.size( self.boundarys[0][0].bcType2 ) == 0:
#             rootBC = self.boundarys[0][0].bcType2[0]
#             if isinstance(rootBC, VaryingElastance):
#                 aortic, mitral = rootBC.aortic, rootBC.mitral
#                 return self.P, self.Q, self.A, rootBC.pressure, rootBC.volume, rootBC.mitralQ, \
#                      aortic.state, aortic.B, aortic.L, mitral.state, mitral.B, mitral.L
        
        print "\nSystem solved!"
        
        
        if self.quiet == False:
            
            print '\n====================================='
            print '___Blood volume - consistency check___'
            
            print 'Vessels  init (ml)  sol (ml)  diff'
            vesselsInit = 0
            vesselsSol  = 0
            for vesselId,vessel in self.vessels.iteritems():
                A1 = self.vessels[vesselId].Asol[0][0:-1]
                A2 = self.vessels[vesselId].Asol[0][1:]
                volumeInit = np.sum(vessel.dz*(A1+A2+np.sqrt(A1*A2))/3.0)*1.e6
                A1 = self.vessels[vesselId].Asol[-1][0:-1]
                A2 = self.vessels[vesselId].Asol[-1][1:]
                volumeSol  = np.sum(vessel.dz*(A1+A2+np.sqrt(A1*A2))/3.0)*1.e6
                diff = volumeInit-volumeSol
                vesselsInit += volumeInit
                vesselsSol  += volumeSol
                print '{:<4}    {:7.2f}    {:7.2f}    {:4.2f}'.format(str(vesselId), volumeInit, volumeSol, diff)
            
            print ' ----------------------------------- '
            print 'Boundarys        in (ml)   out (ml)  '
            totalIn = 0
            totalOut = 0            
            for boundaryList in self.boundarys.itervalues():    
                for boundary in boundaryList:
                    #print '  volume in   (ml)  {:.2f}'.format((abs(boundary.BloodVolumen[0])*1.e6))
                    #print '  volume out  (ml)  {:.2f}'.format((abs(boundary.BloodVolumen[1])*1.e6))
                    #print '  volume diff (ml)  {:.2f}'.format(abs(abs(boundary.BloodVolumen[0])*1.e6 - abs(boundary.BloodVolumen[1])*1.e6))
                    print '{:<12}     {:6.2f}    {:4.2f}'.format(boundary.name,
                                                                 abs(boundary.BloodVolumen[0])*1.e6, 
                                                                 abs(boundary.BloodVolumen[1])*1.e6 ) 
                                                             #abs(abs(boundary.BloodVolumen[0])*1.e6 - abs(boundary.BloodVolumen[1])*1.e6))
                    #print '   {} '.format(boundary.type)
                    totalIn  += abs(boundary.BloodVolumen[0])*1.e6
                    totalOut += abs(boundary.BloodVolumen[1])*1.e6
            print ' ----------------------------------- '
            print 'total'
            print '  vessels initial  (ml)  {:4.2f}'.format(vesselsInit)  
            print '  vessels solution (ml)  {:4.2f}'.format(vesselsSol)  
            print '  boundarys in     (ml)  {:4.2f}'.format(totalIn)
            print '  boundarys out    (ml)  {:4.2f}'.format(totalOut)
            print '                    ------------'
            print '  volume diff      (ml)  {:.2f}'.format(vesselsInit - vesselsSol + totalIn - totalOut)
        
        ## stop realtime visualisation
        for communicator in self.communicators.itervalues():           
            try: communicator.stopRealtimeViz()
            except: pass
            
        ### garbage collection
        gc.collect()
        
        
        print "totaltime is", self.totalTime
        Tim=np.linspace(0,self.totalTime,self.nTsteps)
        print "nTsteps is", self.nTsteps

        try:
            
            
            print "FS726: self.vascularNetwork.boundaryConditions[1][0].volume"
            
            import matplotlib.pyplot as plt
            
            fig1 = plt.figure(1)
            plt.plot(self.baroreceptors['0'].PtildLeft)
            fig1.show()
            
            fig2 = plt.figure(2)
            plt.plot(self.baroreceptors['0'].F_cs)
            plt.plot(self.baroreceptors['0'].F_efferent)
            fig2.show()
            
            fig3 = plt.figure(3)
            plt.plot(self.baroreceptors['0'].delta_TPR)
            fig3.show()
            
            fig4 = plt.figure(4)
            plt.plot(self.baroreceptors['0'].delta_Emax)
            fig4.show()
            
            fig5 = plt.figure(5)
            plt.plot(self.baroreceptors['0'].delta_Vusv)
            fig5.show()
            
            fig6 = plt.figure(6)
            plt.plot(self.baroreceptors['0'].delta_T)
            fig6.show()
            
            raw_input()
            
            #plt.plot(self.baroreceptors['0'].MStrain)
            #plt.show()
            
            #plt.plot(self.venousPool.Vvector)
            #plt.show()
            
            
            #f, axarr =plt.subplots(3)
            #axarr[0].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].pressure/133,Tim,self.vascularNetwork.boundaryConditions[0][0].aortaP/133)
            #axarr[1].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].Flow)
            #axarr[2].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].volume*10**6)
            #axarr[0].set_title("Pressure in LV and aorta")
            #axarr[1].set_title("Volume flow")
            #axarr[2].set_title("Volume in LV")
            #plt.show(f)
#             f, axarr =plt.subplots(5)
#             axarr[0].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].pressure/133,Tim,self.vascularNetwork.boundaryConditions[0][0].aortaP/133)
#             axarr[1].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].volume*10**6)
#             axarr[2].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].aortic.state)
#             axarr[3].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].mitral.state)
#             axarr[4].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].Elastance)
#             axarr[0].set_title("Pressure in LV")
#             axarr[1].set_title("Volueme in LV")
#             axarr[2].set_title("aortic state")
#             axarr[3].set_title("Mitral state")
#             plt.show(f)
#             
#             f2, axarr2 =plt.subplots(3)
#             axarr2[0].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].aortic.state)
#             axarr2[1].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].Flow)
#             axarr2[2].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].DtFlow)
#             plt.show(f2)
#             
#             f3,axarr3=plt.subplots(6)
#             axarr3[0].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].aortic.state)
#             axarr3[1].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].Flow)
#             axarr3[2].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].DtFlow)
#             axarr3[3].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].Turb)
#             axarr3[4].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].Inert)
#             axarr3[5].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].deltaP)
#             
#             plt.show(f3)
#             
#             f4,axarr4=plt.subplots(4)
#             axarr4[0].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].aortic.state)
#             axarr4[1].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].Turb)
#             axarr4[2].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].Inert)
#             axarr4[3].plot(Tim,self.vascularNetwork.boundaryConditions[0][0].InbyTurb)
#             
#             plt.show(f4)
            
            
            
            
            
#             plt.plot(Tim,self.vascularNetwork.boundaryConditions[0][0].volume*10**6)
#             
#             plt.show()
#             plt.plot(Tim,self.vascularNetwork.boundaryConditions[0][0].aortic.state)
#             plt.show()
#             plt.plot(Tim,self.vascularNetwork.boundaryConditions[0][0].mitral.state)
#             plt.show()
        except: pass
            
        
                
        try:
            print "FS 1010 mean strain"
            print  np.mean(self.baroreceptors['0'].MStrain[7300:9080])
            print np.amax(self.baroreceptors['0'].MStrain[7300:9080])
            print np.amin(self.baroreceptors['0'].MStrain[7300:9080])
            #print self.baroreceptors['0'].data['MStrain']
#            import matplotlib.pyplot as plt
#            plt.plot(self.baroreceptors['0'].data['HR'])
            pass
            
        except: pass
            
            
        
        
        del self.numericalObjects
        del self.fields
        del self.connections
        del self.boundarys
        del self.communicators
                
