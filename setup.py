from distutils.core import setup

setup(name='pr0ntools',
	version='1.0',
	description='Integrated circuit reverse engineering research and development',
	package_dir={
			'pr0ntools': 'lib/pr0ntools',
			'pr0ntools.image': 'lib/pr0ntools/image',
			'pr0ntools.jssim': 'lib/pr0ntools/jssim',
			'pr0ntools.stitch': 'lib/pr0ntools/stitch',
			'pr0ntools.stitch.pto': 'lib/pr0ntools/stitch/pto',
			'pr0ntools.tile': 'lib/pr0ntools/tile',
			'pr0ntools.util': 'lib/pr0ntools/util',
			},
	packages=[
			'pr0ntools',
			'pr0ntools.image',
			'pr0ntools.jssim',
			'pr0ntools.stitch',
			'pr0ntools.stitch.pto',
			'pr0ntools.tile',
			'pr0ntools.util',
			],
	author='John McMaster',
	author_email='JohnDMcMaster@gmail.com',
	url='https://github.com/JohnDMcMaster/pr0ntools/',
)

