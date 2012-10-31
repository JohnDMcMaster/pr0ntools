import json

# FIXME: look into support multilevel default dictionary
class Config:
    defaults = {
        "live_video": True,
        "startup_run": False,
        "objective_json": "objective.json",
        "scan_json": "scan.json",
        "multithreaded": True,
        "imager": "VC",
        "cnc": {
            # Good for testing and makes usable to systems without CNC
            "engine": "mock"
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

    def get_scan_config(self):
        return json.loads(open(self['scan_json']).read())
        

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
        # Objective parameters
        self.obj_config = None
        # What to image
        self.scan_config = None

        # Set to true if should try to mimimize hardware actions
        self.dry = False
        
    def writej(self, j, fname, dirname):
        # print json.dumps(j, sort_keys=True, indent=4)
        open('%s\\%s' % (dirname, fname), 'w').write(json.dumps(j, sort_keys=True, indent=4))
        
    def write_to_dir(self, dirname):
        if self.uscope_config:
            self.writej(self.uscope_config, 'microscope.json', dirname)
        if self.scan_config:
            self.writej(self.scan_config, 'scan.json', dirname)
        if self.obj_config:
            self.writej(self.obj_config, 'objective.json', dirname)

