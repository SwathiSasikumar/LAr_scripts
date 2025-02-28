#!/usr/bin/env python

import glob
import argparse
import ROOT
import numpy as np
from datetime import datetime

def main():
    """Read command line and trigger processing"""

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputDir", default = "FCCSW_ecal/baseline_LAr_testResol_1/",
            help = "Directory containing the input files to process", type=str)
    parser.add_argument("-o", "--outFile", default = "out.json",
            help = "Output XGBoost training file", type=str)
    parser.add_argument("--json", help = "json file containing Up/Down corrections", type=str)
    parser.add_argument("clusters", help = "Cluster collection to use", type=str)
    args = parser.parse_args()
    run(args.inputDir, args.clusters, args.outFile, args.json)




def run(in_directory, clusters, out_file, json_updo):
    """Actual processing"""
    init_stuff()


    df = ROOT.ROOT.RDataFrame("events", in_directory+"/*.root")
    num_init = df.Count()
    cells = clusters[:-1] + "Cells"
    df = (
        df
        .Define("E_truth_v", "sqrt(genParticles.momentum.y*genParticles.momentum.y+genParticles.momentum.x*genParticles.momentum.x+genParticles.momentum.z*genParticles.momentum.z)")
        .Define("Truth_E", "E_truth_v[0]")
        .Define(f"{clusters}_EnergyInLayers", f"getCaloCluster_energyInLayers({clusters}, {cells}, 12)")
        .Alias(f"clusters_energy", f"{clusters}.energy")
        .Define(f"lc_idx", f"ArgMax(clusters_energy)")
        .Define(f"Cluster_E", f"clusters_energy[lc_idx]")
        )
    for i in range(12):
        df = df.Define(f"{clusters}_E{i}", f"getFloatAt({i})({clusters}_EnergyInLayers)")
        df = df.Define(f"Cluster_E{i}", f"{clusters}_E{i}[lc_idx]")

    cols_to_use = ["Truth_E", "Cluster_E"]
    cols_to_use += [f"Cluster_E{i}" for i in range(12)]
    v_cols_to_use = ROOT.std.vector('string')(cols_to_use)
    # Filter to remove weird events and get a proper tree
    d = df.Filter("Cluster_E5!=0 && Cluster_E!=0") #.Snapshot("events", out_file, v_cols_to_use)
    print("We have run on", num_init.GetValue(), "events")

    # Study weird events where clusters don't have cells properly attached
    #df.Filter("Cluster_E5==0").Snapshot("events", "problems.root")

    # Training is so fast it can be done online
    cols = d.AsNumpy(v_cols_to_use)

    layers = np.array(
    [
        cols["Cluster_E0"],
        cols["Cluster_E1"],
        cols["Cluster_E2"],
        cols["Cluster_E3"],
        cols["Cluster_E4"],
        cols["Cluster_E5"],
        cols["Cluster_E6"],
        cols["Cluster_E7"],
        cols["Cluster_E8"],
        cols["Cluster_E9"],
        cols["Cluster_E10"],
        cols["Cluster_E11"],
    ]
    )

    cluster_E = layers.sum(axis=0)
    normalized_layers = np.divide(layers, cluster_E)

    label = cols["Truth_E"] / cluster_E
    weights = -np.log10(cols["Truth_E"]) + 3
    #weights = 1/label**.5
    data = np.vstack([normalized_layers, cluster_E])

    # Somehow importing those libraries earlier in the script does not work. Bad interaction with
    # ROOT libraries in loadGeometry...
    from sklearn.model_selection import RandomizedSearchCV
    import scipy.stats as stats
    import xgboost as xgb
    
    # Even do fancy Hyperparameter optimization for the lulz
    param_dist_XGB = {'max_depth': stats.randint(3, 12), # default 6
                      'n_estimators': stats.randint(300, 800), #default 100
                      'learning_rate': stats.uniform(0.1, 0.5),#def 0.3 
                      'subsample': stats.uniform(0.5, 1)} 

    #reg = xgb.XGBRegressor(tree_method="approx", objective='reg:squaredlogerror')
    reg = xgb.XGBRegressor(tree_method="hist")

    #gsearch = RandomizedSearchCV(estimator = reg, 
                        #param_distributions = param_dist_XGB, n_iter=10,cv=3)
    #gsearch.fit(data.T, label, sample_weight=weights)
    #print ("Best parameters : ",gsearch.best_params_)
    #print ("Best score (on train dataset CV) : ",gsearch.best_score_)

    # Did HPO once. Now use best fit values for almost instant training
    #reg.objective = 'reg:squaredlogerror'
    #{'learning_rate': 0.11716471738296005, 'max_depth': 6, 'n_estimators': 627, 'subsample': 0.5345527598172761}
    reg.subsample = 0.5
    reg.max_depth = 6
    reg.n_estimators = 650
    reg.learning_rate = 0.12
    #reg.subsample = 0.8
    #reg.max_depth = 4
    #reg.n_estimators = 700
    #reg.learning_rate = 0.32
    print("Start training")
    beg = datetime.now()
    reg.fit(data.T, label, sample_weight=weights, verbose=True)
    #reg.fit(data.T, label)
    end = datetime.now()
    print("Done in ", end-beg)
    reg.save_model(out_file)

    #res = reg.predict(data.T)
    #a = np.array([label, res])
    #print(a)


def init_stuff():
    readoutName = "ECalBarrelPhiEta"
    geometryFile = "../../FCCDetectors/Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectMaster.xml"
    ROOT.gROOT.SetBatch(True)
    ROOT.gSystem.Load("libFCCAnalyses")
    _fcc = ROOT.dummyLoader
    ROOT.gInterpreter.Declare("using namespace FCCAnalyses;")
    ROOT.gInterpreter.Declare("using namespace FCCAnalyses::CaloNtupleizer;")
    ROOT.CaloNtupleizer.loadGeometry(geometryFile, readoutName)
    ROOT.ROOT.EnableImplicitMT(32)


if __name__ == "__main__":
    main()

    #ROOT.gInterpreter.Declare("""
    #float generatedE(const ROOT::RDF::RSampleInfo &id) {
        #TString s(id.AsString());
        #TPRegexp tpr("_(\\\\d+)\\\\.root");
        #TString ss = s(tpr);
        #TString e_string = ss(1, ss.Index('.')-1);
        #return e_string.Atof() / 1000.;
    #}
    #""")


