import os
from Gaudi.Configuration import *


from Configurables import ApplicationMgr
ApplicationMgr().EvtSel = 'None' 
ApplicationMgr().EvtMax = 1
ApplicationMgr().OutputLevel = INFO

# DD4hep geometry service
from Configurables import GeoSvc
## parse the given xml file
path_to_detectors = os.environ.get("FCCDETECTORS", "")
geoservice = GeoSvc("GeoSvc")
geoservice.detectors = [
                          #os.path.join(path_to_detectors, 'Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectMaster.xml'),
                          os.path.join(path_to_detectors, 'Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectMaster_forX0.xml'),
                          #os.path.join(path_to_detectors, 'Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectEmptyMaster.xml'),
                       ]
geoservice.OutputLevel = INFO 
ApplicationMgr().ExtSvc += [geoservice]

from Configurables import MaterialScan
# Material scan is done from the interaction point to the end of world volume.
# In order to use other end boundary, please provide the name of a thin, e.g. cylindrical volume.
# For instance adding envelopeName="BoundaryPostCalorimetry" will perform the scan only till the end of calorimetry.
# BoundaryPostCalorimetry is defined in Detector/DetFCChhECalInclined/compact/envelopePreCalo.xml
materialservice = MaterialScan("GeoDump")
materialservice.filename = "out_material_scan.root"
materialservice.etaBinning = 0.05
materialservice.etaMax = 0.9
materialservice.nPhiTrials = 10
ApplicationMgr().ExtSvc += [materialservice]


