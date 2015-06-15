

import sys,os
cur = os.path.dirname(os.path.realpath('__file__'))
sys.path.append(cur+'/../')


#sys.path.append(''.join([cur,'/../NetworkLib']))
from NetworkLib.classVascularNetwork import VascularNetwork

#sys.path.append(''.join([cur,'/../SolverLib']))
from SolverLib.class1DflowSolver import FlowSolver

#sys.path.append(''.join([cur,'/../UtilityLib']))
from UtilityLib import moduleXML

import gc,time

import multiprocessing

## module to run simulations as a batch jobs

def runBatchAsSingleProcess(batchDataList, quiet = False):
    '''
    Run a set of simulations on one core without multiprocessing
    
    Input:
        batchDataList <list> := with data for each batch job [batchData1, batchData .. ]
            batchData <list> := list with [networkName, dataNumber, networkXmlFile, pathSolutionDataFilename]
        
    '''
    timeStartBatch = time.time()
    print '====================================='
    print '------Single Process Batch Job-------'
    print 'numberOfEval.:   {}'.format(len(batchDataList))
    for batchData in batchDataList:
        minutesSolve,secsSolve = runSingleBatchSimulation(batchData)
        if quiet == False:
            print '____________Batch   {:5} ___________'.format(batchDataList.index(batchData)) 
            print 'Runtime:        {} min {} sec'.format(minutesSolve,secsSolve)
    timeBatchJob= time.time()-timeStartBatch
    minutesBatch = int(timeBatchJob/60.)
    secsBatch = timeBatchJob-minutesBatch*60.
    print '====================================='
    print 'total runtime:  {} min {} sec'.format(minutesBatch,secsBatch)
    print '====================================='
  
def runSingleBatchSimulation(batchData):
    '''
    Function which runs a single simulation the defined with batchData
    
    Input:
        batchData <list> := list with [networkName, dataNumber, networkXmlFile, pathSolutionDataFilename]
    '''
    timeStart = time.clock()
    networkName,dataNumber,networkXmlFile,pathSolutionDataFilename = batchData
    vascularNetworkTemp = moduleXML.loadNetworkFromXML(networkName, dataNumber, networkXmlFile = networkXmlFile, pathSolutionDataFilename = pathSolutionDataFilename)
    vascularNetworkTemp.quiet = True
    flowSolver = FlowSolver(vascularNetworkTemp, quiet=True)
    flowSolver.solve()
    vascularNetworkTemp.saveSolutionData()
    del flowSolver
    gc.collect()
    timeSolverSolve = time.clock()-timeStart
    minutesSolve = int(timeSolverSolve/60.)
    secsSolve = timeSolverSolve-minutesSolve*60.
    return minutesSolve,secsSolve

def runBatchAsMultiprocessing(batchDataList, numberWorkers = None, quiet = False):
    '''
    Run a set of simulations on one core without multiprocessing
    
    Input:
        batchDataList <list> := with data for each batch job [batchData1, batchData .. ]
            batchData <list> := list with [networkName, dataNumber, networkXmlFile, pathSolutionDataFilename]
        
    '''
    if numberWorkers == None: numberWorkers = multiprocessing.cpu_count()
    timeStartBatch = time.time()
    print '====================================='
    print '------Multiprocessing Batch Job------'
    print 'numberWorkers:   {}'.format(numberWorkers)
    print 'numberOfEval.:   {}'.format(len(batchDataList))
    pool = multiprocessing.Pool(numberWorkers)
    results = pool.map(runSingleBatchSimulation,batchDataList)
    pool.close() 
    pool.join()
    if quiet == False:
        print '====================================='
        for batchJobIndex,[minutesSolve,secsSolve] in enumerate(results):
            print '____________Batch   {:5} ___________'.format(batchJobIndex+1) 
            print 'Runtime:        {} min {} sec'.format(minutesSolve,secsSolve)
        print '====================================='
    timeBatchJob= time.time()-timeStartBatch
    minutesBatch = int(timeBatchJob/60.)
    secsBatch = timeBatchJob-minutesBatch*60.
    print 'total runtime:  {} min {} sec'.format(minutesBatch,secsBatch)
    print '====================================='
            