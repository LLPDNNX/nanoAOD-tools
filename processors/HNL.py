import os
import sys
import math
import json
import argparse
import random
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
from importlib import import_module
from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor
from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection, Object
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module
from PhysicsTools.NanoAODTools.modules import *
#from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetmetHelperRun2       import * 
#from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetRecalib import *

parser = argparse.ArgumentParser()
parser.add_argument('--isData', dest='isData', action='store_true',default=False)
parser.add_argument('--year', dest='year', action='store',type=int, default=2016)
parser.add_argument('--input', dest='inputFiles', action='append',default=[])
parser.add_argument('output', nargs=1)

args = parser.parse_args()


print "isData:",args.isData
print "inputs:",len(args.inputFiles)
for inputFile in args.inputFiles:
    print "2018" in inputFile
    if "2016" in inputFile:
        year = 2016
    elif "2017" in inputFile:
        year = 2017
    elif "2018" in inputFile:
        year = 2018
    else:
        year = args.year
    rootFile = ROOT.TFile.Open(inputFile)
    if not rootFile:
        print "CRITICAL - file '"+inputFile+"' not found!"
        sys.exit(1)
    tree = rootFile.Get("Events")
    if not tree:
        print "CRITICAL - 'Events' tree not found in file '"+inputFile+"'!"
        sys.exit(1)
    print " - ",inputFile,", events=",tree.GetEntries()
    
print "year:",year
print "output directory:",args.output[0]

globalOptions = {
    "isData":args.isData,
    "year":year
}

isMC = not args.isData

minMuonPt = {2016: 25., 2017: 28., 2018: 25.}


if isMC : 

	jecTags = {	2016 : 'Summer16_07Aug2017_V11_MC',
			2017 : 'Fall17_17Nov2017_V32_MC',
			2018 : 'Autumn18_V19_MC'
	}



	jerTags = {	2016 : 'Summer16_25nsV1_MC',
			2017 : 'Fall17_V3_MC',
			2018 : 'Autumn18_V7_MC'
        }
if args.isData : 

	jecTags = {	2016 : 'Summer16_07Aug2017All_V11_DATA',
			2017 : 'Fall17_17Nov2017_V32_DATA',
			2018 : 'Autumn18_V19_DATA'
        }


muonSelection = [
    EventSkim(selection=lambda event: event.nTrigObj>0),
    MuonSelection(
        outputName="tightMuon",
        storeKinematics=['pt','eta', 'dxy', 'dxyErr', 'dz', 'dzErr', 'phi', 'pfRelIso04_all'],
        storeWeights=True,
        muonMinPt = minMuonPt[globalOptions["year"]],
        triggerMatch = True,
        muonID = MuonSelection.TIGHT,
        muonIso = MuonSelection.TIGHT,
        selectLeadingOnly=True,
        globalOptions=globalOptions
    ),
    EventSkim(selection=lambda event: event.ntightMuon==1),
    MuonSelection(
        inputCollection = lambda event: event.tightMuon_unselected,
        outputName="looseMuons",
        storeKinematics=['pt','eta', 'dxy', 'dxyErr', 'dz', 'dzErr', 'phi', 'pfRelIso04_all', 'tightId'],
        storeWeights=True,
        muonMinPt = 5.,
        muonID = MuonSelection.LOOSE,
        muonIso = MuonSelection.NONE,
        globalOptions=globalOptions
    ),
    
    SingleMuonTriggerSelection(
        inputCollection=lambda event: event.tightMuon,
        outputName="IsoMuTrigger",
        storeWeights=True,
        globalOptions=globalOptions
    ),
    EventSkim(selection=lambda event: event.IsoMuTrigger_flag==1),
    EventSkim(selection=lambda event: event.nlooseMuons>0)
]

#analyzerChain = [jetRecalibration]
analyzerChain = []

analyzerChain.extend(muonSelection)

analyzerChain.append(
    JetSelection(
        leptonCollection=lambda event: event.tightMuon,
        globalOptions=globalOptions
    )
)

analyzerChain.append(EventSkim(selection=lambda event: len(event.selectedJets)>0))


analyzerChain.append(
    InvariantSystem(
        inputCollection = lambda event: [event.looseMuons[0], event.tightMuon[0]],
        outputName = "dimuon"
    )
)

analyzerChain.append(
    LepJetFinder(
        jetCollection = lambda event: event.selectedJets,
        leptonCollection = lambda event: event.looseMuons,
    )
)



modelPath = {2016: "PhysicsTools/NanoAODTools/data/nn/weight2016_75.pb",
            2017: "PhysicsTools/NanoAODTools/data/nn/weight2017_68.pb",
            2018: "PhysicsTools/NanoAODTools/data/nn/weight2018_73.pb"
            }

analyzerChain.append(
    TaggerEvaluation(
        modelPath=modelPath[year],
        logctauValues = range(-1, 4),
        inputCollections=[
            lambda event: event.lepJet,
        ],
        taggerName="llpdnnx",
    )
)


analyzerChain.append(
    JetTaggerResult(
        inputCollection = lambda event: event.lepJet,
        taggerName = "llpdnnx",
        outputName = "lepJet",
        logctauValues = range(-1, 4),
    )
)


analyzerChain.append(
    JetTruthFlags(inputCollection= lambda event: event.lepJet,
        globalOptions=globalOptions,
        outputName="lepJet"
    )
)



analyzerChain.append(
    JetMetUncertainties(
	era = globalOptions["year"],
	globalTag=jecTags[globalOptions["year"]],
	jerTag = jerTags[globalOptions["year"]],
	isData= args.isData 
    )
)

analyzerChain.append( 
     	MetFilter(
     		globalOptions=globalOptions,
     		outputName="MET_filter"
     	)
)

analyzerChain.append(
     EventObservables(
       jetCollection = lambda event: event.selectedJets,
       leptonCollection = lambda event: event.tightMuon[0] 
     )
)
'''
 
analyzerChain.append(
    XGBEvaluation(
        modelPath="PhysicsTools/NanoAODTools/data/nn/bdt.model",
    )
)
'''

storeVariables = [
    [lambda tree: tree.branch("MET_pt", "F"), lambda tree,event: tree.fillBranch("MET_pt", event.MET_pt)],
    [lambda tree: tree.branch("MET_phi", "F"), lambda tree,event: tree.fillBranch("MET_phi", event.MET_phi)],
    [lambda tree: tree.branch("MET_significance", "F"), lambda tree,event: tree.fillBranch("MET_significance", event.MET_significance)],
    [lambda tree: tree.branch("PV_npvs", "I"), lambda tree,event: tree.fillBranch("PV_npvs", event.PV_npvs)],
    [lambda tree: tree.branch("PV_npvsGood", "I"), lambda tree,event: tree.fillBranch("PV_npvsGood", event.PV_npvsGood)],
    [lambda tree: tree.branch("fixedGridRhoFastjetAll", "F"), lambda tree,event: tree.fillBranch("fixedGridRhoFastjetAll", event.fixedGridRhoFastjetAll)],
    #[lambda tree: tree.branch("bdt_score", "F"), lambda tree,event: tree.fillBranch("bdt_score", event.bdt_score)]
]

if not globalOptions["isData"]:
    storeVariables.append([lambda tree: tree.branch("genweight","F"),lambda tree,event: tree.fillBranch("genweight",event.Generator_weight)])


analyzerChain.append(EventInfo(storeVariables=storeVariables))

analyzerChain.append(
    PileupWeight(
        outputName ="puweight",
        globalOptions=globalOptions
    )
)

p=PostProcessor(
    args.output[0],
    [args.inputFiles],
    modules=analyzerChain,
    maxEvents=-1,
    friend=True
)
p.run()
