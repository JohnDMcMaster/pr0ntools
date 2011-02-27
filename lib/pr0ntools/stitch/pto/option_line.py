'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

'''
#hugin_optimizeReferenceImage 0
#hugin_blender enblend
#hugin_remapper nona
#hugin_enblendOptions 
#hugin_enfuseOptions 
#hugin_hdrmergeOptions 
#hugin_outputLDRBlended true
#hugin_outputLDRLayers false
#hugin_outputLDRExposureRemapped false
#hugin_outputLDRExposureLayers false
#hugin_outputLDRExposureBlended false
#hugin_outputLDRExposureLayersFused false
#hugin_outputHDRBlended false
#hugin_outputHDRLayers false
#hugin_outputHDRStacks false
#hugin_outputLayersCompression LZW
#hugin_outputImageType tif
#hugin_outputImageTypeCompression LZW
#hugin_outputJPEGQuality 100
#hugin_outputImageTypeHDR exr
#hugin_outputImageTypeHDRCompression LZW
'''

import os
import shutil
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.execute import Execute
import comment_line

class OptionLine(comment_line.CommentLine):
	
	def __init__(self, text, project):
		comment_line.CommentLine.__init__(self, text, project)
		
	'''
	def update(self):
		# Update to the correct indexes
		# Wonder if this can all go on a single line?
		# Would validate my k/v paradigm
		for k in self.variables:
			self.set_variables(k, self.image.get_index())
	'''
	
	@staticmethod
	def from_line(line, pto_project):
		ret = OptionLine()
		ret.text = line
		return ret

