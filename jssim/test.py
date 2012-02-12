from pr0ntools.jssim.layer import UVPolygon, Net, Nets, PolygonRenderer, Point, Layer

l1 = Layer.from_svg('diffusion.svg')
l2 = Layer.from_svg('polysilicon.svg')
print 'Subtracting...'
li = l1.subtract(l2)
lil = li.to_layer()
lil.show()

