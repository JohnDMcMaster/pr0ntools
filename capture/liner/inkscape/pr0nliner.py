#!/usr/bin/env python

# http://wiki.inkscape.org/wiki/index.php/PythonEffectTutorial

# These two lines are only needed if you don't put the script directly into
# the installation directory
import sys
sys.path.append('/usr/share/inkscape/extensions')

# We will use the inkex module with the predefined Effect base class.
import inkex
# The simplestyle module provides functions for style parsing.
from simplestyle import *

class PathifyEffect(inkex.Effect):
    def __init__(self):
        """
        Constructor.
        Defines the "--what" option of a script.
        """
        # Call the base class constructor.
        inkex.Effect.__init__(self)

    def effect(self):
        # Get access to main SVG document element and get its dimensions.
        svg = self.document.getroot()

        # Create a new layer
        layer = inkex.etree.SubElement(svg, 'g')
        layer.set(inkex.addNS('label', 'inkscape'), 'output')
        layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')

        '''
        Inkscape represents paths as a special transform element + a relative path
        Why not make all absolute?
        Makes differences easier?
        wait...
            <g
            transform="translate(-167.57144,-304.50507)"
            ...
            <path
               transform="translate(167.57144,304.50507)"
       they cancel out
       
        <g
           inkscape:groupmode="layer"
           id="layer2"
           inkscape:label="ref"
           style="display:inline">
              <path
                 style="fill:#0000ff;fill-opacity:1;stroke:none;display:inline;stroke-opacity:1"
                 d="m 62.857143,71.428571 114.285717,0 0,312.857139 -114.285717,0 z"
                 id="path3013"
                 inkscape:connector-curvature="0" />
        </g>
        '''
        style = { 'fill':'#00ff00', 'fill-opacity':1,
                    'stroke':'none', 'stroke-opacity':1,
                    'display':'inline' }
        poly_attributes = {'style':formatStyle(style),
                        'd':'m 62.857143,71.428571 114.285717,0 0,312.857139 -114.285717,0 z'}
        # Above didn't put it in the svg namespace, does it matter?
        inkex.etree.SubElement(layer, inkex.addNS('path','svg'), poly_attributes )


# Create effect instance and apply it.
effect = PathifyEffect()
effect.affect()

