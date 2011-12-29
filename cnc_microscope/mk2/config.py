import json

if 0:
	microscope_config_file_name = 'microscope_small.json'
	scan_config_file_name = 'scan_small.json'
else:
	microscope_config_file_name = 'microscope.json'
	scan_config_file_name = 'scan.json'

def get_microscope_config():
	microscope_config_file = open(microscope_config_file_name)
	microscope_config = json.loads(microscope_config_file.read())
	return microscope_config
	
def get_scan_config():
	scan_config_file = open(scan_config_file_name)
	scan_config = json.loads(scan_config_file.read())
	return scan_config

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
		self.objective_config = None
		# What to image
		self.scan_config = None

		# Set to true if should try to mimimize hardware actions
		self.dry = False
		
	def writej(self, j, fname, dirname):
		# print json.dumps(j, sort_keys=True, indent=4)
		open('%s\\%s' % (dirname, fname), 'w').write(json.dumps(j, sort_keys=True, indent=4))
		
	def write_to_dir(self, dirname):
		if self.microscope_config:
			self.writej(self.microscope_config, 'microscope.json', dirname)
		if self.scan_config:
			self.writej(self.scan_config, 'scan.json', dirname)
		if self.objective_config:
			self.writej(self.objective_config, 'objective.json', dirname)

