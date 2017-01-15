'''
This file is part of pr0ntools
Image utility file
http://effbot.org/imagingbook/image.htm
http://pillow.readthedocs.io/en/3.1.x/reference/ImagePalette.html

Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from PIL import Image
import os

# needed for PNG support
# rarely used and PIL seems to have bugs
PALETTES = bool(os.getenv('PR0N_PALETTES', ''))

class PImage:
    # We do not copy array, so be careful with modifications
    def __init__(self, image):
        # A PIL Image object
        self.image = None
        self.temp_file = None
        
        if image is None:
            raise Exception('cannot construct on empty image')
        self.image = image
    
    def debug_print(self, char_limit = None, row_label = False):
        for y in range(0, self.height()):
            row_label_str = ''
            if row_label:
                row_label_str = '%02d: ' % y
            print row_label_str + self.debug_row_string(y, char_limit, row_label_str)
    
    def debug_row_string(self, y, char_limit = None, row_label = None):
        if row_label is None:
            row_label = ''
        ret = row_label
        x_max = self.width()
        for x in range(0, x_max):
            if not x == 0:
                ret += " "
            ret += "% 4s" % repr(self.get_pixel(x, y))
            if char_limit and len(ret) > char_limit:
                ret = ret[0:char_limit]
                break

        return ret

    # To an Image
    def to_image(self):
        return self.image
    
    '''
    First step in scaling is to take off any whitespace
    This normalizes the spectra
    Returns a new image that is trimmed
    '''
    def trim(self):
        (image, _x_min, _x_max, _y_min, _y_max) = self.trim_verbose()
        return image
        
    def trim_verbose(self):
        #print 'Trimming: start'
        # Set to lowest set pixel
        # Initially set to invalid values, we should replace them
        # I'm sure there are more effient algorithms, but this "just works" until we need to up performance
        # What we probably should do is scan in from all sides until we hit a value and then stop
        x_min = self.width()
        x_max = -1
        y_min = self.height()
        y_max = -1
        for y in range(0, self.height()):
            for x in range(0, self.width()):
                # print "%s != %s" % (self.get_pixel(x, y), self.white())
                # if set, we have a value influencing the result
                if self.get_pixel(x, y) != self.white():
                    x_min = min(x_min, x)
                    y_min = min(y_min, y)
                    x_max = max(x_max, x)
                    y_max = max(y_max, y)
    
        #print (x_min, x_max, y_min, y_max)
        #print 'Trimming: doing subimage'
        return (self.subimage(x_min, x_max, y_min, y_max), x_min, x_max, y_min, y_max)
    
    def save(self, *args, **kwargs):
        '''save(file name[, format, kw options]) where kw_options includes quality=<val>'''
        self.image.save(*args, **kwargs)

    def get_scaled(self, factor, filt = None):
        if filt is None:
            filt = Image.NEAREST
        i = self.image.resize((int(self.width() * factor), int(self.height() * factor)), filt)
        return PImage.from_image(i)

    '''
    Given exclusive end array bounds (allows .width() convenience)
    returns a new image trimmed to the given bounds
    Truncates the image if our array bounds are out of range
        Maybe we should throw exception instead?
    '''
    def subimage(self, x_min, x_max, y_min, y_max):    
        if x_min is None:
            x_min = 0
        if x_max is None:
            x_max = self.width()
        if y_min is None:
            y_min = 0
        if y_max is None:
            y_max = self.height()
        #print 'subimage: start.  x_min: %d: x_max: %d, y_min: %d, y_max: %d' % (x_min, x_max, y_min, y_max)

        if x_min < 0 or y_min < 0 or x_max < 0 or y_max < 0:
            print x_min, y_min, x_max, y_max
            raise Exception('out of bounds')

        # Did we truncate the whole image?
        if x_min > x_max or y_min > y_max:
            return self.from_array([], self.get_mode(), self.get_mode())
        
        '''
        height = y_max - y_min + 1
        width = x_max - x_min + 1

        array_out = [[0 for i in range(width)] for j in range(height)]
        for cur_height in range(0, height):
            for cur_width in range(0, width):
                array_out[cur_height][cur_width] = self.get_pixel(cur_height + y_min, cur_width + x_min)

        #print 'subimage: beginning from array'
        return self.from_array(array_out, self.get_mode(), self.get_mode())
        '''
        # 4-tuple (x0, y0, x1, y1)
        #print 'x_min: %d, y_min: %d, x_max: %d, y_max: %d' % (x_min, y_min, x_max, y_max)
        # This is exclusive, I want inclusive
        return PImage.from_image(self.image.crop((x_min, y_min, x_max, y_max)))

    def copy(self):
        return self.subimage(None, None, None, None)

    def rotate(self, degrees):
        return PImage.from_image(self.image.rotate(degrees))
        
    def width(self):
        return self.image.size[0]
    
    def height(self):
        return self.image.size[1]
    
    def set_pixel(self, x, y, pixel):
        self.image.putpixel((x, y), pixel)
    
    def get_pixel(self, x, y):
        try:
            return self.image.getpixel((x, y))
        except:
            print 'bad pixel values, x: %d, y: %d' % (x, y)
            raise
    
    # The following are in case we change image mode
    def black(self):
        '''return the instance's representation of black'''
        mode = self.get_mode()
        if mode == "1":
            return 1
        if mode == "L":
            return 0
        if mode == "RGB":
            return (255, 255, 255)
        raise Exception('Bad mode %s' % mode)
    
    def white(self):
        '''return the instance's representation of white'''
        mode = self.get_mode()
        if mode == "1":
            return 0
        if mode == "L":
            return 255
        if mode == "RGB":
            return (0, 0, 0)
        raise Exception('Bad mode %s' % mode)
    
    def pixel_to_brightness(self, pixel):
        '''Convert pixel to brightness value, [0.0, 1.0] where 0 is white and 1 is black'''
        # The above range was chosen somewhat arbitrarily as thats what old code did (think because thats what "1" mode does)
        # Also, it makes it convenient for summing up "filled" areas as we usually assume (infinite) white background
        mode = self.get_mode()
        if mode == "1":
            # TODO: double check this is correct, that is 0 is white and 1 is black
            return pixel * 1.0
        if mode == "L":
            # 255 is white
            return 1.0 - (1 + pixel) / 256.0
        if mode == "RGB":
            # RGB represents (255, 255, 255) as white since all colors are at max
            # Also scale to the range correctly by adding 3 and then invert to make it luminescence
            return 1.0 - (pixel[0] + pixel[1] + pixel[2] + 3) / (256.0 * 3)
        raise Exception('Bad mode %s' % mode)
    
    def get_mode(self):
        return self.image.mode

    def file_name(self):
        return self.image.fp.name

    def set_canvas_size(self, width, height):
        # Simple case: nothing to do
        if self.width() == width and self.height == height:
            return
        
        ip = Image.new(self.image.mode, (width, height))
        if PALETTES and self.image.palette:
            ip.putpalette(self.image.palette)
        ip.paste(self.image, (0,0))
        # Shift the old image out
        self.image = ip

    def paste(self, img, x, y):
        #self.image.paste(img, (x, y))
        # left, upper, right, and lower
        self.image.paste(img.image, (x, y, x + img.width(), y + img.height()))
        
    @staticmethod
    def from_file(path):
        '''
        I'm having difficulty dealing with anything paletted, so convert everything right off the bat
        '''
        if not type(path) in (str, unicode):
            raise Exception()

        img = Image.open(path)
        if img is None:
            raise Exception("Couldn't open image file: %s" % path)
        if False:
            img_converted = img.convert('L')
            return PImage.from_image(img_converted)
        else:
            return PImage.from_image(img)

    @staticmethod
    def from_image(image):
        return PImage(image)
    
    @staticmethod
    def from_blank(width, height, mode="RGB"):
        '''Create a blank canvas'''
        return PImage.from_image(Image.new(mode, (width, height)))

    @staticmethod
    def from_fns(*args, **kwargs):
        return PImage.from_image(from_fns(*args, **kwargs))
        
    @staticmethod
    def from_unknown(image, trim=False):
        if isinstance(image, str):
            ret = PImage.from_file(image)
        elif isinstance(image, PImage):
            ret = image
        elif isinstance(image, image.Image):
            ret = PImage.from_image(image)
        else:
            raise Exception("unknown parameter: %s" % repr(image))
        if trim:
            ret = ret.trim()
        return ret

    @staticmethod
    def get_pixel_mode(pixel):
        '''Tries to guess pixel mode.  Hack to transition some old code, don't use this'''
        # FIXME: make sure array mode matches our created image
        if type(pixel) == type(0):
            return "L"
        if len(pixel) == 3:
            return 'RGB'
        else:
            return "L"
            
    @staticmethod
    def from_array(array, mode_in = None, mode_out = None):
        '''
        array[y][x]
        '''
        #print 'from_array: start'
        # Make a best guess, we should probably force it though
        if mode_in is None:
            mode_in = PImage.get_pixel_mode(array[0][0])
        if mode_out is None:
            mode_out = mode_in
            
        ret = None
        height = len(array)
        if height > 0:
            width = len(array[0])
            if width > 0:
                # (Xsize, Ysize)
                # Feed in an arbitrary pixel and assume they are all encoded the same
                # print 'width: %d, height: %d' % (width, height)
                ret = PImage(Image.new(mode_out, (width, height), "White"))
                for y in range(0, height):
                    for x in range(0, width):
                        # print 'x: %d, y: %d' % (x, y)
                        ret.set_pixel(x, y, array[y][x])
        if ret is None:
            ret = PImage(Image.new(mode_out, (0, 0), "White"))
        #print 'from_array: end'
        return ret

    @staticmethod
    def is_image_filename(filename):
        return filename.find('.tif') > 0 or filename.find('.jpg') > 0 or filename.find('.png') > 0 or filename.find('.bmp') > 0

def from_fns(images_in, tw=None, th=None):
    '''
    Return an image constructed from a 2-D array of image file names
    [[r0c0, r0c1],
     [r1c0, r1c1]]
    '''
    mode = None
    
    rows = len(images_in)
    cols = len(images_in[0])
    im = None
    src_last = None
    # Ensure all images loaded
    for rowi in range(rows):
        row = images_in[rowi]
        if len(row) != cols:
            raise Exception('row size mismatch')
        for coli in range(cols):
            # Ensure its a PImge object
            src = images_in[rowi][coli]
            if src is None:
                # Can we make a best guess on what to fill in?
                if not src_last:
                    continue
                
                # im should in theory work but accessing pixels
                # is for some reason causing corruption
                iml = Image.open(src_last)
                imf = Image.new(mode, (tw, th))
                if PALETTES:
                    imf.putpalette(iml.palette)
                pix = iml.getpixel((tw - 1, th - 1))
                imf.paste(pix, (0, 0, tw, th))
                
                images_in[rowi][coli] = imf
            else:
                im = Image.open(src)
                imw, imh = im.size
                
                if mode is None:
                    mode = im.mode
                elif im.mode != mode:
                    raise Exception('mode mismatch')
                
                if tw is None:
                    tw = imw
                elif tw != imw:
                    raise Exception('tile width mismatch: %s has %s vs %s' % (src, tw, imw))
                
                if th is None:
                    th = imh
                elif th != imh:
                    raise Exception('tile height mismatch')
                
                images_in[rowi][coli] = im

            src_last = src or src_last
    
    # Images are now all either PImage or None with uniform width/height
    width = tw * cols
    height = th * rows
    ret = Image.new(mode, (width, height))
    # Copy palette over from last png, if possible
    if PALETTES and im and im.palette:
        ret.putpalette(im.palette)
    
    #ret = im.copy()
    #ret.resize((width, height))
    
    for rowi in range(rows):
        for coli in range(cols):
            src = images_in[rowi][coli]
            # Allowed to be empty
            if src:
                # (left, upper)
                cpix = coli * tw
                rpix = rowi * th
                ret.paste(src, (cpix, rpix))
    #ret = im_reload(ret)
    return ret

# Change canvas, shifting pixels to fill it
def rescale(im, factor, filt=Image.NEAREST):
    w, h = im.size
    ret = im.resize((int(w * factor), int(h * factor)), filt)
    # for some reason this breaks the image
    # but for other similiar operations its required
    if 0 and im.palette:
        ret.putpalette(im.palette)
    return ret

# Change canvas, not filling in new pixels
def resize(im, width, height, def_color=None):
    if PALETTES and im.palette:
        # Lower right corner is a decent default
        # since will probably have a (black) border
        xy = tuple([x - 1 for x in im.size])
        def_color = im.getpixel(xy)
        ret = Image.new(im.mode, (width, height), def_color)
        # WARNING: workaround for PIL bugs
        # don't use putpalette(im.palette)
        # it mixes up RGB and RGB;L
        ret.putpalette(im.palette.tobytes())
    else:
        ret = Image.new(im.mode, (width, height))
    
    ret.paste(im, (0, 0))
    return ret

def im_reload(im):
    im.save('/tmp/pt_pil_tmp.png')
    return Image.open('/tmp/pt_pil_tmp.png')
