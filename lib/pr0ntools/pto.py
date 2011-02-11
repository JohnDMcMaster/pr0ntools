'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

'''
Example file

	p f2 w3000 h1500 v360  n"JPEG q90"
	m g1 i0

	i w2816 h600 f0 a0 b-0.01 c0 d0 e0 p0 r0 v180 y0  u10 n"/tmp/0.6621735916207697.png"
	i w2816 h600 f0 a=0 b=0 c=0 d0 e0 p0 r0 v=0 y0  u10 n"/tmp/0.5022987786350409.png"

	v p1 r1 y1

	# numbers index into above images
	c n0 N1 x983.515978 y31.390674 X860.944595 Y132.080243 t0
	c n0 N1 x652.899413 y71.500283 X807.577503 Y201.843139 t0
	c n0 N1 x474.578071 y154.235865 X107.943696 Y223.202780 t0
	c n0 N1 x774.903103 y186.724081 X1830.890967 Y429.024407 t0
	c n0 N1 x1201.353730 y299.329003 X1269.005225 Y511.798210 t0
	c n0 N1 x1708.592510 y359.149116 X1873.061084 Y499.156064 t0
	c n0 N1 x192.653946 y158.115483 X80.809197 Y254.420106 t0
'''
class PTOProject:
	# File name, if one exists
	file_name = None
	# Raw project text, None is not loaded
	text = None
	# If this is a temporary project, have it delete upon destruction
	temp_file = None

	def __init__():
		pass
	
	@staticmethod
	def from_file_name(file_name, is_temporary = False):
		ret = PTOProject()
		ret.file_name = file_name
		if is_temporary:
			ret.temp_file = ManagedTempFile.from_existing(file_name)
		return ret

	@staticmethod
	def from_text(text):
		ret = PTOProject()
		ret.text = text
		return ret

	def get_text(self):
		if self.text:
			return self.text
		self.text = open(file_name).read()
		return self.text

	def get_a_file_name(self):
		'''If doesn't have a real file, create a temp file'''
		if self.file_name:
			return self.file_name
		self.temp_file = ManagedTempFile.get(None, ".pto")
		self.file_name = self.temp_file.file_name

	def merge(others):
		'''Return a project containing both control points'''
		'''
		[mcmaster@gespenst bin]$ pto_merge --help
		pto_merge: merges several project files
		pto_merge version 2010.4.0.854952d82c8f

		Usage:  pto_merge [options] input.pto input2.pto ...

		  Options:
			 -o, --output=file.pto  Output Hugin PTO file.
									Default: <filename>_merge.pto
			 -h, --help			 Shows this help
		'''
		pto_temp_file = TempFile.get(None, ".pto")

		command = "pto_merge"
		args = list()
		
		args.append("--output=%s", pto_temp_file)

		args.append(pto_temp_file.file_name())
		for other in others:
			 args.append(other.get_a_file_name())

		# go go go
		(rc, output) = Execute.with_output(command, args)
		if not rc == 0:
			raise Exception('failed pto_merge')
		return PTOProject.from_file_name(pto_temp_file, True)

