import json
import os

'''
A few general assumptions:
-Camera is changed rarely.  Therefore only one camera per config file
-Objectives are changed reasonably often
    They cannot changed during a scan
    They can be changed in the GUI
'''

# FIXME: look into support multilevel default dictionary
class Config:
    defaults = {
        "live_video": True,
        "objective_json": "objective.json",
        "scan_json": "scan.json",
        "multithreaded": True,
        "imager": {
            "engine":'mock',
            "snapshot_dir":"snapshot",
            "width": 3264,
            "height": 2448,
            "mag": 10.0,
            # Using 10.0X relay lens and ~8MP camera
            # I far oversample
            # maybe helps with bayer filter though 
            "scalar": 0.5,
       },
        "cnc": {
            # Good for testing and makes usable to systems without CNC
            "engine": "mock",
            "startup_run": False,
            "startup_run_exit": False,
            "out_dir":"out",
            "overwrite":False,
            # Default to no action, make movement explicit
            # Note that GUI can override this
            "dry":True,
        }
    }
    
    def __init__(self, fn):
        self.j = json.loads(open('microscope.json').read())
    
    def __getitem__(self, name):
        if name in self.j:
            return self.j[name]
        else:
            return Config.defaults[name]
    
    def __setitem__(self, name, value):
        self.j[name] = value
    
    def __delete__(self, name):
        del self.j[name]

class UScopeConfig(Config):
    pass

config = UScopeConfig('microscope.json')
# TODO: merge objective.json into microscope.json
uscope_config = config

class RunConfig:
    def __init__(self):
        # Robotic controller if availible
        # right now this is the MC object
        self.controller = None
        # Imaging device
        # Right now this is a PIL based object
        self.imager = None
        # Callback for progress
        self.progress_cb = None
        
        self.job_name = None
        
        # Comprehensive config structure
        self.microcope_config = None
        # What to image
        self.scan_config = None

        # Set to true if should try to mimimize hardware actions
        self.dry = False
        
    def writej(self, j, fname, dirname):
        # print json.dumps(j, sort_keys=True, indent=4)
        open(os.path.join(dirname, fname), 'w').write(json.dumps(j, sort_keys=True, indent=4))
        
    def write_to_dir(self, dirname):
        self.writej(config.j, 'microscope.json', dirname)
        if self.scan_config:
            self.writej(self.scan_config, 'scan.json', dirname)

