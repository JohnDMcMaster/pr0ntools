#!/usr/bin/python
'''
pr0nstitchaj: AJ's autopano WINE wrapper for Hugin
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools.stitch.pto.project import PTOProject
import sys 
import os.path
import argparse

VERSION = '0.1'

def arg_fatal(s):
	print s
	help()
	sys.exit(1)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="create Hugin .pto using Andrew Jenny's autopano")
	
	image_file_names = list()
	project_file_names = list()
	
	project = PTOProject.from_file_name('out.pto')
	project.parse()
	
	
	
	# Overall exposure
	# *very* important
	project.panorama_line.set_variable('E', 1)
	# What about m's p and s?

	for image_line in project.image_lines:
		# Don't adjust exposure
		image_line.set_variable('Eev', 1)
		# blue and red white balance correction at normal levels
		image_line.set_variable('Eb', 1)
		image_line.set_variable('Er', 1)
		# Disable EMoR corrections
		image_line.set_variable('Ra', 0)
		image_line.set_variable('Rb', 0)
		image_line.set_variable('Rc', 0)
		image_line.set_variable('Rd', 0)
		image_line.set_variable('Re', 0)
	
	project.regen()
	#print project.get_text()
	project.save()
	
	print 'Done!'

