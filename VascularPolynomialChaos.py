########################################################################################
#                            Vascular Polynomial Chaos 0.3
########################################################################################
##
# created by Vinzenz Eck vinzenz.eck@mytum.de
# uses polynomial Chaos toolbox from Jonathan Feinberg, Simula Center Oslo
##

import sys,os
cur = os.path.dirname(os.path.realpath('__file__'))

#from NetworkLib.classVascularNetwork import VascularNetwork
### another unnecessary import.

#from SolverLib.class1DflowSolver import FlowSolver
### another

import VascularPolynomialChaosLib.classVpcConfiguration as cVPCConf
import VascularPolynomialChaosLib.classDistributionManager as cDistMng
import VascularPolynomialChaosLib.moduleFilePathHandlerVPC as mFPH_VPC
import VascularPolynomialChaosLib.moduleBatchSimulationManager as mBSM
import VascularPolynomialChaosLib.classLocationOfInterestManager as cLocOfIntrMng
import VascularPolynomialChaosLib.classConfigurationUQSA as cConfigUQSA

import UtilityLib.moduleStartUp as mStartUp
import UtilityLib.moduleXML as mXML

import chaospy as cp
import pprint

import numpy as np

import cPickle

def vascularPolyChaos():
    '''
    Perform vascular polynomial chaos
    or MonteCarlo analysis for STARFiSh simulation case
    # steps
    # 1. load vpc case and configuration

    # 2. create distributions

    # 3. add dependentCase if existent

    # 4. create samples

    # 5. evaluate model / on local machine or on server

    # 6. postprocess evaluated data, peak finding etc

    # 7. create Orthogonal polynomials

    # 8. calculate polynomial chaos expansion

    # 9. uncertainty quantfication, sensitivity analysis
    '''
    print ""
    print '=============================================='
    print '#        VascularPolynomialChaos_v0.3        #'
    print '=============================================='
    # steps
    # 1. load vpc case and configuration
    optionsDict = mStartUp.parseOptions(['f','n'],vascularPolynomialChaos=True)
    networkName = optionsDict['networkName']
    dataNumber  = optionsDict['dataNumber']
    
    # 1.1 load configuration and locations of interest       
    configurationUQSA = cConfigUQSA.ConfigurationUQSA()
    configurationFilePath = mFPH_VPC.getFilePath('vpcConfigXmlFile', networkName, dataNumber, 'read')
    configurationUQSA.loadXMLFile(configurationFilePath)
    
    vpcConfiguration          = configurationUQSA.vpcConfiguration
    locationOfInterestManager = configurationUQSA.locationOfInterestManager
    locationOfInterestManager.initialize() # initialize the location of interest
    
    # 1.2 load vascular network file polynomial chaos
    vpcNetworkXmlFile = mFPH_VPC.getFilePath('vpcNetworkXmlFile', networkName, dataNumber, 'read')
    vascularNetwork = mXML.loadNetworkFromXML(networkName, dataNumber, networkXmlFile = vpcNetworkXmlFile)
    # 1.3 print defined random variables
    assert len(vascularNetwork.randomInputManager.randomInputs) != 0, "VascularPolynomialChaos_v0.3: no random inputs defined!"
    vascularNetwork.randomInputManager.printOutInfo()
    
    # 2. create distributions
    distributionManager = cDistMng.DistributionManagerChaospy(vascularNetwork.randomInputManager.randomInputVector)
    distributionManager.createRandomVariables()

    # 3. add dependentCase if existent 
    # TODO: add correlation matrix to xml definitions and variable dependentCase to definitions
    a = 0.5
    CorrelationMatrix = np.array([[1.,a,a],
                                  [a,1.,a],
                                  [a,a,1.]])
    dependentCase = False
       
    if dependentCase == True:
        # this enables dependentCase in Distribution Manager
        distributionManager.createDependentDistribution(CorrelationMatrix)
        
    ## do the analysis for all defined polynomial orders:
    for polynomialOrder in vpcConfiguration.polynomialOrders:
        # 4. create samples
        if vpcConfiguration.createSample == True:
            distributionManager.createSamples(vpcConfiguration.sampleMethod, expansionOrder = polynomialOrder)
            
            vpcSampleFile = mFPH_VPC.getFilePath('vpcSampleFile', networkName, dataNumber, mode = "write", gPCEmethod=vpcConfiguration.sampleMethod, gPCEorder=polynomialOrder)
            distributionManager.saveSamples(networkName)
        else:
            vpcSampleFile = mFPH_VPC.getFilePath('vpcSampleFile', networkName, dataNumber, mode = "read", gPCEmethod=vpcConfiguration.sampleMethod, gPCEorder=polynomialOrder)
            distributionManager.loadSamples(vpcSampleFile)

        # 5. evaluate model / on local machine or on server
        # 5.1 create evaluation case file list
        evaluationCaseFiles = [] # list of [ [networkName,dataNumber,xml-filePath(LOAD) ,xml-filePath(SAVE), hdf-filePath] for each evaluation
        for simulationIndex in xrange(distributionManager.samplesSize):
            vpcNetworkXmlEvaluationFileLoad = mFPH_VPC.getFilePath('vpcEvaluationNetworkXmlFile', networkName, dataNumber, 'write',
                                                               gPCEmethod=vpcConfiguration.sampleMethod, gPCEorder= polynomialOrder, evaluationNumber=simulationIndex)
            vpcEvaluationSolutionDataFile = mFPH_VPC.getFilePath('vpcEvaluationSolutionDataFile', networkName, dataNumber, 'write',
                                                               gPCEmethod=vpcConfiguration.sampleMethod, gPCEorder= polynomialOrder, evaluationNumber=simulationIndex)
            vpcNetworkXmlEvaluationFileSave = vpcNetworkXmlEvaluationFileLoad
            evaluationCaseFiles.append([networkName,dataNumber,vpcNetworkXmlEvaluationFileLoad,vpcNetworkXmlEvaluationFileSave,vpcEvaluationSolutionDataFile])
        # 5.2 save/create simulation xml files
        if vpcConfiguration.createEvaluationXmlFiles == True:
            for sampleIndex in xrange(distributionManager.samplesSize):
                # update network with current evaluation number
                distributionManager.passRealisation(sampleIndex)
                vpcNetworkXmlEvaluationFile = evaluationCaseFiles[sampleIndex][2]
                mXML.writeNetworkToXML(vascularNetwork,  dataNumber = dataNumber, networkXmlFile= vpcNetworkXmlEvaluationFile)
            
            evaluationLogFile = mFPH_VPC.getFilePath('evaluationLogFile', networkName, dataNumber, mode = "write", gPCEmethod=vpcConfiguration.sampleMethod, gPCEorder=polynomialOrder)
            vascularNetwork.randomInputManager.saveRealisationLog(evaluationLogFile, networkName, dataNumber, method = ''.join(['PolynomialChaos-Ord ',str(polynomialOrder)]), samplingScheme = vpcConfiguration.sampleMethod)
        # 5.3 run evaluation simulations
        if vpcConfiguration.simulateEvaluations == True:
            if vpcConfiguration.localEvaluation == True:
                startIndex = 0
                endIndex   = int(distributionManager.samplesSize)
                newRange = vpcConfiguration.evaluationNumbers
                if len(newRange) == 2:
                    # check if the indices are avaliable
                    if all([i in xrange(distributionManager.samplesSize) for i in newRange]):
                        if newRange[0] < newRange[1]:
                            startIndex = newRange[0]
                            endIndex   = newRange[1]
                batchFileList = evaluationCaseFiles[startIndex:endIndex+1]
                if vpcConfiguration.multiprocessing == False:
                    mBSM.runBatchAsSingleProcess(batchFileList, quiet = True)
                else:
                    mBSM.runBatchAsMultiprocessing(batchFileList, vpcConfiguration.numberOfProcessors , quiet = True)
            else: print "server simulations not implemented yet";exit() # TODO: server simulations not implemented yet

        print "starting Post processing "
        # 6. process quantity of interest
        locationOfInterestManager.sampleSize = distributionManager.samplesSize
        
        if vpcConfiguration.preProcessData == True:
            locationOfInterestManager.preprocessSolutionData(evaluationCaseFiles)

        if vpcConfiguration.postProcessing == True:
            # if polynomial chaos
            # 7. create Orthogonal polynomials
            distributionManager.calculateOrthogonalPolynomials()
            # 8. uncertainty quantfication, sensitivity analysis based on polynomial chaos expansion
            locationOfInterestManager.calculateStatisticsPolynomialChaos(distributionManager)
            
            vpcQuantityOfInterestFile = mFPH_VPC.getFilePath('vpcSolutionDataFile', networkName, dataNumber, mode = "write",  gPCEmethod=vpcConfiguration.sampleMethod, gPCEorder=polynomialOrder)
            locationOfInterestManager.saveQuantitiyOfInterestData(vpcQuantityOfInterestFile)
            ## if monte carlo
            # 9. uncertainty quantfication, sensitivity analysis based on Monte Carlo simulation
            #locationOfInterestManager.calculateStatisticsMonteCarlo()
            
        # 10. plotting of variables
if __name__ == '__main__':
    vascularPolyChaos()
