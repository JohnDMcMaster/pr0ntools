from matplotlib.pyplot import show

from hcluster import pdist, linkage, dendrogram
import numpy
from numpy.random import rand

X = rand(10,100)
X[0:5,:] *= 2
Y = pdist(X)
Z = linkage(Y)
dendrogram(Z)

show()

