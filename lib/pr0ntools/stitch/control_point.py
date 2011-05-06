'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.temp_file import ManagedTempDir
from pr0ntools.execute import Execute
from pr0ntools.stitch.pto.project import PTOProject
import shutil
import os.path

# clear; rm -f /tmp/*.pto /tmp/*.jpg; pr0nstitch --result=out.jpg *.jpg

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

#class ControlPointGenerator:	
class AutopanoSiftC:
	'''
	Example stitch command
	"autopano-sift-c" "--maxmatches" "0" "--maxdim" "10000" "out.pto" "first.png" "second.png"
	'''
	def generate_core(self, image_file_names):
		project_file = ManagedTempFile.get(None, ".pto")

		command = "autopano-sift-c"
		args = list()
		
		# Try to post process them to make them more accurate
		#args.append("--refine")
		
		# Perform RANSAC to try to get bad control points out
		#args.append("--ransac")
		#args.append("on")

		# Unlimited matches
		args.append("--maxmatches")
		args.append("0")
		
		# ?
		#args.append("--maxdim")
		#args.append("10000")

		# Project file
		args.append(project_file.file_name)
		
		# Images
		for image_file_name in image_file_names:
			 args.append(image_file_name)

		# go go go
		(rc, output) = Execute.with_output(command, args)
		if not rc == 0:
			print
			print
			print
			print 'output:\n%s' % output
			raise Exception('Bad rc: %d' % rc)
		
		# We return PTO object, not string
		return PTOProject.from_temp_file(project_file)


#class AutopanoAJ : ControlPointGenerator:	
class ControlPointGenerator:
	'''
	autopano.exe /f /tmp/file1.jpg /tmp/file2.jpg /project:hugin 
	Example stitch command
	Will result in .pto in being in /tmp though
	
	Eh its pretty unreliable (wine issue?) if we don't put pix in current dir
	Easiest way to accomplish this without copying is to create temp dir and symlink
	we are editing the files anyway, so not a big deal
	'''
	def generate_core(self, image_file_names):
		command = "autopanoaj"
		args = list()
		final_project_file = ManagedTempFile.get(None, ".pto")
		temp_dir = ManagedTempDir.get()
		
		# default is .oto
		args.append("/project:hugin")
		# Use image args instead of dir
		
		# Images
		image_links = dict()
		for image_file_name in image_file_names:
			# args.append(image_file_name.replace("/tmp/", "Z:\\tmp\\"))
			image_file_name = os.path.realpath(image_file_name)

			link_file_name = os.path.join(temp_dir.file_name, os.path.basename(image_file_name))
			print 'Linking %s -> %s' % (link_file_name, image_file_name)
			os.symlink(image_file_name, link_file_name)

		#sys.exit(1)
		# go go go
		(rc, output) = Execute.with_output(command, args, temp_dir.file_name)
		print 'Finished control point pair execution'
		if not rc == 0:
			print
			print
			print
			print 'output:\n%s' % output
			raise Exception('Bad rc: %d' % rc)
		
		'''
		Doesn't like the match:
		PICTURE PAIRS VALIDATION 
		  Pair (  0,  1)
			Ransac (In : 21, Out : 4, Residu : 4.43799)
			REMOVED
		  Timing : 583.7 us
		'''
		if output.find('REMOVED') >= 0:
			print 'WARNING: RANSAC invalidated control points'
			return None
		
		output_file_name = os.path.join(temp_dir.file_name, "panorama0.pto")
		
		# This happens occassionally, not sure why
		if not os.path.exists(output_file_name):
			print 'WARNING: missing output pto file!'
			return None
		
		# We return PTO object, not string
		# Ditch the gen file because its unreliable
		shutil.move(output_file_name, final_project_file.file_name)
		f = open(final_project_file.file_name, 'r')
		project_text = f.read()
		# Under WINE, do fixup
		# #-imgfile 2816 704 "Z:\tmp\pr0ntools_471477ADA1679A2E\pr0ntools_3CD1C0B1BB218E40.jpg"
		project_text = project_text.replace('Z:\\', '/').replace('\\', '/')
		for image_file_name in image_file_names:
			link_file_name = os.path.join(temp_dir.file_name, os.path.basename(image_file_name))
			print 'Replacing %s -> %s' % (link_file_name, image_file_name)
			project_text = project_text.replace(link_file_name, image_file_name)

		if False:
			print
			print 'Raw control point project (after symbolic link and WINE file name substitution)'
			print
			print
			print project_text
			print
			print
			print
		#sys.exit(1)
		f.close()
		f = open(final_project_file.file_name, 'w')
		f.write(project_text)
		project = PTOProject.from_temp_file(final_project_file)
		return project
		
		
























class ControlPointGeneratorXX:
	'''
	autopano.exe /f /tmp/file1.jpg /tmp/file2.jpg /project:hugin 
	Example stitch command
	Will result in .pto in being in /tmp though
	'''
	def generate_core(self, image_file_names):
		command = "autopanoaj"
		args = list()
		project_file = ManagedTempFile.get(None, ".pto")
		
		# default is .oto
		args.append("/project:hugin")
		# Use image args instead of dir
		args.append("/f");
		args.append('/path:Z:\\tmp')
		
		# Images
		for image_file_name in image_file_names:
			 args.append(image_file_name.replace("/tmp/", "Z:\\tmp\\"))

		# go go go
		(rc, output) = Execute.with_output(command, args)
		if not rc == 0:
			raise Exception('Bad rc: %d' % rc)
		
		# We return PTO object, not string
		# Ditch the gen file because its unreliable
		shutil.move("/tmp/panorama0.pto", project_file.file_name)
		f = open(project_file.file_name, 'r')
		project_text = f.read()
		# Under WINE, do fixup
		project_text = project_text.replace('Z:\\tmp\\', '/tmp/')
		print
		print
		print
		print project_text
		print
		print
		print
		#sys.exit(1)
		f.close()
		f = open(project_file.file_name, 'w')
		f.write(project_text)
		return PTOProject.from_temp_file(project_file)

