import argparse
import os
import glob
import re
from shutil import copyfile

def parse_html(fn):
    is_gmap = False
    layer_name = '???'
    chip_name = '???'
    copyright = ''
    
    for l in open(fn):
        is_gmap |= bool(re.search(r'maps.google.com/maps/api', l))

        # <title>SiMap: CBM 65CE02 (top metal2) @ Mit20x</title>
        m = re.match(r'<title>(.*)</title>', l)
        if m:
            s = m.group(1)
            s = s.replace('SiMap: ', '')
            chip_name = s

        # copyrightNode.innerHTML = "&copy;2016 John McMaster, CC BY";
        m = re.match(r'copyrightNode.innerHTML = "&copy;(.*)";', l)
        if m:
            copyright = m.group(1)

    if is_gmap:
        assert chip_name
        return layer_name, chip_name, copyright
    else:
        return None


def run():
    src_dir = 'tiles_out'
    dst_dir = 'l1-tiles'

    assert os.path.exists(src_dir)
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)

    maxx = 0
    maxy = 0

    for src_zoom_dir in glob.glob('%s/*' % src_dir):
        print("Zoom %s" % src_zoom_dir)
        src_level = int(os.path.basename(src_zoom_dir))
        dst_level = src_level + 1
        dst_zoom_dir = "%s/%s" % (dst_dir, dst_level)
        if not os.path.exists(dst_zoom_dir):
            os.mkdir(dst_zoom_dir)

        # level/xcoord/ycoord.jpg
        for src_fn in glob.glob('%s/*' % src_zoom_dir):
            # y001_x000.jpg
            m = re.match(r'.*/y(.*)_x(.*).jpg', src_fn)
            assert m, src_fn
            y = int(m.group(1))
            x = int(m.group(2))
            maxx = int(max(x, maxx))
            maxy = int(max(y, maxy))
            x_dir = '%s/%s' % (dst_zoom_dir, x)
            if not os.path.exists(x_dir):
                os.mkdir(x_dir)

            dst_fn = "%s/%s.jpg" % (x_dir, y)
            copyfile(src_fn, dst_fn)

    tileSize = 250
    width = (maxx + 1) * tileSize
    height = (maxy + 1) * tileSize

    index = None
    if os.path.exists('index.html'):
        index = parse_html('index.html')
    if index:
        os.rename("index.html", "index_gmap.html")
    else:
        index = parse_html('index_gmap.html')
        assert index

    layer_name, chip_name, copyright = index
    print('Chip: %s' % chip_name)
    print('Layer: %s' % layer_name)
    print('Copyright: %s' % copyright)

    chip_name_raw = chip_name
    if copyright:
        chip_name += ', &copy;%s' % copyright

    open('index.html', 'w').write('''\
<!DOCTYPE html>
<html>
  <head>
    <title>Loading...</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script type="text/javascript" src="http://siliconpr0n.org/lib/groupXIV/35-jpg/public_html/bundle/groupxiv.js"></script>
    <link type="text/css" rel="stylesheet" href="http://siliconpr0n.org/lib/groupXIV/35-jpg/public_html/bundle/groupxiv.css">
</head>
<body>
    <div id="viewer"></div>
    <script>
    initViewer({"scale": null, "layers": [{"imageSize": 4096, "width": %u, "height": %u, "URL": "l1", "tileSize": %u, "name": "%s"}], "name": "%s", "name_raw": "%s", "copyright": "%s"});
    </script>
</body>
</html>
''' % (width, height, tileSize, layer_name, chip_name, chip_name_raw, copyright))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot')
    #parser.add_argument('fin1',  help='Input csv')
    args = parser.parse_args()

    run()
