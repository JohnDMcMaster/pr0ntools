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
