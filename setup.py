from distutils.core import setup

with open('README') as file:
    long_description = file.read()

setup(name='pr0ntools',
	version='1.0',
	comment='Integrated circuit reverse engineering research and development',
	description='Integrated circuit reverse engineering research and development',
	long_description = long_description,
	package_dir={
			'pr0ntools': 'lib/pr0ntools',
			'pr0ntools.image': 'lib/pr0ntools/image',
			'pr0ntools.jssim': 'lib/pr0ntools/jssim',
			'pr0ntools.jssim.cif': 'lib/pr0ntools/jssim/cif',
			'pr0ntools.jssim.files': 'lib/pr0ntools/jssim/files',
			'pr0ntools.stitch': 'lib/pr0ntools/stitch',
			'pr0ntools.stitch.pto': 'lib/pr0ntools/stitch/pto',
			'pr0ntools.tile': 'lib/pr0ntools/tile',
			'pr0ntools.util': 'lib/pr0ntools/util',
			},
	packages=[
			'pr0ntools',
			'pr0ntools.image',
			'pr0ntools.jssim',
			'pr0ntools.jssim.cif',
			'pr0ntools.jssim.files',
			'pr0ntools.stitch',
			'pr0ntools.stitch.pto',
			'pr0ntools.tile',
			'pr0ntools.util',
			],
	scripts=[
			'stitch/pr0nmap.py',
			'stitch/pr0npto.py',
			'stitch/pr0nstitchaj.py',
			'stitch/pr0nstitch.py',
			'stitch/pr0ntile.py',
			'stitch/pr0nts.py',
			'stitch/sandbox.py',
			],
	author='John McMaster',
	author_email='JohnDMcMaster@gmail.com',
	url='https://github.com/JohnDMcMaster/pr0ntools/',
)

