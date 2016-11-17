import sys,os
cur = os.path.dirname(os.path.realpath('__file__'))
sys.path.append(cur+'/../')

from VascularPolynomialChaosLib.testBaseClass import TestBaseClass 
import VascularPolynomialChaosLib.moduleBatchSimulationManager as mBatchSim


import moduleFilePathHandlerVNR as mFPH_VNR
import VascularNetworkReductionLib.classNetworkReduction as cNred

import UtilityLib.moduleXML as mXML
import UtilityLib.progressBar as cPB
import pickle


import time
import numpy as np
import multiprocessing

class ReductionCase(TestBaseClass):
    
    externVariables      = { 'caseName'                 : TestBaseClass.ExtValue(str, strCases = ['anything']),
                             'dataNumber'               : TestBaseClass.ExtValue(str, strCases = ['anything']),
                             'simulationDescription'    : TestBaseClass.ExtValue(str, strCases = ['anything']), 
                             'createNetworks'           : TestBaseClass.ExtValue(bool),
                             'solveNetworks'            : TestBaseClass.ExtValue(bool),
                             'batchDataFile'            : TestBaseClass.ExtValue(str, strCases = ['anything']),
                             'batchDataStart'           : TestBaseClass.ExtValue(int),
                             'batchDataEnd'             : TestBaseClass.ExtValue(int),      
                             'postProcessing'           : TestBaseClass.ExtValue(bool),               
                             'multiprocessing'          : TestBaseClass.ExtValue(bool),  
                             'numberOfProcessors'       : TestBaseClass.ExtValue(int),
                             'useAverageValues'         : TestBaseClass.ExtValue(bool),
                             'useVesselsImpedance'      : TestBaseClass.ExtValue(bool),
                             'useLumpedValues'          : TestBaseClass.ExtValue(bool)
                           } 
    
    externXmlAttributes  = []
    
    externXmlElements    = ['caseName',
                            'dataNumber',
                            'simulationDescription',
                            'createNetworks',
                            'solveNetworks',
                            'batchDataFile',
                            'batchDataStart',
                            'batchDataEnd',
                            'postProcessing',                 
                            'multiprocessing',
                            'numberOfProcessors',
                            'useAverageValues',
                            'useVesselsImpedance',
                            'useLumpedValues'
                            ]
    
    
    def __init__(self, CPUTimeFile=None):
        
        self.networkName = None
        self.dataNumber  = None
        
        self.CPUTimeFile = CPUTimeFile
        
        self.caseName = None
        self.simulationDescription = None
        self.createNetworks     = True
        self.solveNetworks     = False
        # ceate simulation case files       
        
        self.batchDataFile = None
        self.batchDataStart = 0
        self.batchDataEnd = -1
        #  run simulations 
        self.multiprocessing        = True
        self.numberOfProcessors     = 8
        self.postProcessing  = True
        
        self.useAverageValues = False
        self.useVesselsImpedance = False
        self.useLumpedValues = False
        
        
    
    
    def loadBatchDatalist(self):
        
        filepath = self.batchDataFile
        batchDataList = pickle.load(open(filepath, 'rb'))
        
        self.batchDataList = batchDataList[self.batchDataStart: self.batchDataEnd]
    
    def createEvaluationCaseFiles(self): 
        '''
        
        batchDataList <list> := with data for each batch job [batchData1, batchData .. ]
            batchData <dict> := dict with {simulationIndex: , networkName: , dataNumber: , networkXmlFile: , pathSolutionDataFilename: 
                                            'reductionNetworkName': , truncateList}
        
        '''
        
        #TODO: replace create evaluation files or save them to disc!!!
        if self.createNetworks == True:
            
            sampleSize = len(self.batchDataList)
            
            progressBar = cPB.ProgressBar(35, sampleSize)
            
            for simulationIndex, batchData in enumerate(self.batchDataList):
                
                networkName = batchData['networkName']
                reductionNetworkName = batchData['reductionNetworkName']
                truncateList = batchData['truncateList']
                dataNumber = self.dataNumber
                
                vascularNetwork = mXML.loadNetworkFromXML(reductionNetworkName, dataNumber = "xxx")
                vascularNetwork.quiet = True
                
                vascularNetwork.update({'description':self.simulationDescription,
                                        'dataNumber' :self.dataNumber})
                
                New_network = cNred.NetworkReduction(vascularNetwork, quiet=True)
                
                New_network.initialize(useAverageValues=self.useAverageValues, 
                                       useVesselsImpedance=self.useVesselsImpedance, 
                                       useLumpedValues=self.useLumpedValues)
                
                New_network.reduceNetworkFromList(truncateList)
                
                New_network.name = networkName
                newNetworkXmlFile =  mFPH_VNR.getFilePath('reductionNetworkXmlFileXXX', networkName, "xxx", 'write', reductionNetworkName=reductionNetworkName, reductionNetworkCase=self.caseName)
                
                mXML.writeNetworkToXML(New_network, dataNumber = dataNumber, networkXmlFile=newNetworkXmlFile)
            

                
                solutionFileXML = mFPH_VNR.getFilePath('reductionNetworkXmlFileSim', networkName, dataNumber, 'write', reductionNetworkName=reductionNetworkName, reductionNetworkCase=self.caseName)
                solutionFilehd5 = mFPH_VNR.getFilePath('reductionSolutionFile', networkName, dataNumber, 'write', reductionNetworkName=reductionNetworkName, reductionNetworkCase=self.caseName)
                
                batchData['networkXmlFileLoad'] = newNetworkXmlFile
                batchData['networkXmlFileSave'] = solutionFileXML
                batchData['pathSolutionDataFilename'] = solutionFilehd5
                batchData['dataNumber'] = self.dataNumber
                
                del vascularNetwork
                del New_network
            
                progressBar.progress(simulationIndex) 
                
        if self.solveNetworks:
            mBatchSim.runBatchAsMultiprocessing(self.batchDataList, CPUTimeFile=self.CPUTimeFile)
            
        
    