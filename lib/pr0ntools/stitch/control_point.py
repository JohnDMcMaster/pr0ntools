'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

"""
class ControlPointGenerator:
	@staticmethod
	def from_string():
		pass

	@staticmethod
	def from_id():
		pass
		
	def generate_core(image_file_names):
		'''
		Input should be a list of either 
		Returns a PTOProject
		'''
		pass

	def generate_by_name(image_file_names):
		'''Takes in a list of image file names'''
		return generate_core(imageFileNames)

	def generate_by_PIL(images):
		'''Takes in a list of TempFilePIL images'''
		return generateControlPointsCore(imageFiles)

class AutopanoAj(ControlPointGenerator):
	os.system("autopanoaj /allinone /project:hugin '/ransac_dist:1.0'")
	os.system("cat %s |sed 's@%s@%s@g' >/tmp/%s" % (project_file, original_dir, image_dir, temp_project_file))
"""

from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.execute import Execute
from pr0ntools.stitch.pto import PTOProject

#class AutopanoSiftC : ControlPointGenerator:	
class ControlPointGenerator:
	'''
	Example stitch command
	"autopano-sift-c" "--maxmatches" "0" "--maxdim" "10000" "out.pto" "first.png" "second.png"
	'''
	def generate_core(self, image_file_names):
		project_file = ManagedTempFile.get(None, ".pto")

		command = "autopano-sift-c"
		args = list()
		
		# Try to post process them to make them more accurate
		args.append("--refine")
		# Perform RANSAC to try to get bad control points out
		args.append("--ransac")

		# Unlimited matches
		args.append("--maxmatches")
		args.append("0")
		
		# ?
		args.append("--maxdim")
		args.append("10000")

		# Project file
		args.append(project_file.file_name)
		
		# Images
		for image_file_name in image_file_names:
			 args.append(image_file_name)

		# go go go
		(rc, output) = Execute.with_output(command, args)
		if not rc == 0:
			raise Exception('Bad rc: %d' % rc)
		
		# We return PTO object, not string
		return PTOProject.from_temp_file(project_file)

