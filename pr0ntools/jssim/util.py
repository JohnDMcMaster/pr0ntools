# For debugging, don't rely on
g_debug_width = 200
g_debug_height = 200

def set_debug_width(width):
	global g_debug_width
	g_debug_width = width
	
def set_debug_height(height):
	global g_debug_height
	g_debug_height = height
	
def get_debug_width():
	global g_debug_width
	return g_debug_width
	
def get_debug_height():
	global g_debug_height
	return g_debug_height

