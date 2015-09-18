


import sys,os
cur = os.path.dirname(os.path.realpath('__file__'))
sys.path.append(cur+'/../')


from classLocationOfInterest import LocationOfInterest
import moduleFilePathHandlerVPC as mFPH_VPC

#sys.path.append(''.join([cur,'/../UtilityLib']))
from UtilityLib import moduleXML

import numpy as np
import h5py

from testBaseClass import TestBaseClass 

class LocationOfInterestManager(TestBaseClass):
    '''
    
    '''
    externVariables      = {'locationsOfInterest' : TestBaseClass.ExtDict({'locationOfInterest': TestBaseClass.ExtObject({'LocationOfInterest':LocationOfInterest})}),
                           } 
    externXmlAttributes  = []
    externXmlElements    = ['locationsOfInterest']
    
    def __init__(self,xmlNode = None, sampleSize = None):
        
        self.locationsOfInterest = {}
        self.sampleSize = sampleSize
                                
        # read data from xml node if the data is provided
        if xmlNode:
            self.readDataFromXmlNode(xmlNode)
        
    def addLocationOfInterest(self,locationId, locationName, quantitiesOfInterestToProcess, xVal, confidenceAlpha):
        '''
        
        '''
        self.locationsOfInterest[locationId] = LocationOfInterest(locationName,quantitiesOfInterestToProcess, xVal, confidenceAlpha)
            
    def loadQuantitiyOfInterestData(self):
        '''
        
        '''
        print "loadQuantitiyOfInterestData() not implemented yet"
        
    def saveQuantitiyOfInterestData(self,networkName,dataNumber,gPCEmethod,gPCEorder):
        '''
        
        '''
        vpcQuantityOfInterestFile = mFPH_VPC.getFilePath('vpcSolutionDataFile', networkName, dataNumber, mode = "write", gPCEmethod=gPCEmethod, gPCEorder=gPCEorder)
        saveFile = h5py.File(vpcQuantityOfInterestFile,'w')
        # add simulation time
        saveFile.create_dataset('simulationTime', data=self.simulationTime)
        for locationId,locationOfInterest in self.locationsOfInterest.iteritems():        
            # add information of each quantity in each location
            locationGroup = saveFile.create_group(locationId)
            locationOfInterest.saveQuantitiyOfInterestData(locationGroup)
        saveFile.flush()
        saveFile.close()
            
    def preprocessSolutionData(self,evaluationCaseFiles):
        '''
        load all samples and pass data to locations of interest
        
        find simulation time array with largest dt
        
        invoke time cropping and post processing for the data        
        '''
        # loop through all solution data files 
        # find time array
        #solutionTime min
        
        numberOfTimePoints = []
        timeStart = []
        timeEnd = []
        
        for networkName,dataNumber,vpcNetworkXmlEvaluationFile,vpcNetworkXmlEvaluationFileSave,vpcEvaluationSolutionDataFile in evaluationCaseFiles:
            vascularNetwork = moduleXML.loadNetworkFromXML(networkName, dataNumber, networkXmlFile = vpcNetworkXmlEvaluationFile, pathSolutionDataFilename = vpcEvaluationSolutionDataFile)
            vascularNetwork.linkSolutionData()
            
            numberOfTimePoints.append(len(vascularNetwork.simulationTime))
            timeStart.append(min(vascularNetwork.simulationTime))
            timeEnd.append(max(vascularNetwork.simulationTime))
                        
            vascularNetwork.solutionDataFile.close()
            del vascularNetwork
        
        self.simulationTime = np.linspace(max(timeStart), min(timeEnd), min(numberOfTimePoints))
        
        # pass the data to the locationsOfInterests which will load the information needed
        for sampleIndex,[networkName,dataNumber,vpcNetworkXmlEvaluationFile,vpcNetworkXmlEvaluationFileSave,vpcEvaluationSolutionDataFile] in enumerate(evaluationCaseFiles):
            vascularNetwork = moduleXML.loadNetworkFromXML(networkName, dataNumber, networkXmlFile = vpcNetworkXmlEvaluationFile, pathSolutionDataFilename = vpcEvaluationSolutionDataFile)
            vascularNetwork.linkSolutionData()
            for locationOfInterest in self.locationsOfInterest.values():
                locationOfInterest.preprocessSolutionData(vascularNetwork,self.simulationTime, self.sampleSize, sampleIndex)
        
        # second postprocessing find extrema if needed
        for locationOfInterest in self.locationsOfInterest.values():
            locationOfInterest.preprocessSolutionDataExtremaAndInflectionPoints(self.simulationTime, self.sampleSize)
                         
                        
    def calculateStatisticsPolynomialChaos(self,distributionManager):
        '''
        Calculate statisitcs for each quantity of interest at each location of interest based
        on the generalized polynomial chaos expansion.
        '''
        for locationOfInterest in self.locationsOfInterest.values():
            for quantity in locationOfInterest.quantitiesOfInterestToProcess:
                locationOfInterest.quantitiesOfInterest[quantity].calculateStatisticsPolynomialChaos(distributionManager)
                
    
    def calculateStatisticsMonteCarlo(self):
        '''
        Calculate statisitcs for each quantity of interest at each location of interest based
        on a Monte Carlo simulation
        '''
        pass
        for locationOfInterest in self.locationsOfInterest:
            for quantity in locationOfInterest.quantitiesOfInterestToProcess:
                locationOfInterest.quantitiesOfInterest[quantity].calculateStatisticsMonteCarlo()
                        
