# requires numpy and PyMix (matplotlib is just for making a histogram)
import random
import numpy as np
from matplotlib import pyplot as plt
import mixture

random.seed(010713)  # to make it reproducible

# create a mixture of normals:
#  1000 from N(0, 1)
#  2000 from N(6, 2)
mix = np.concatenate([np.random.normal(0, 1, [1000]),
                      np.random.normal(6, 2, [2000])])

# histogram:
plt.hist(mix, bins=20)
plt.savefig("mixture.png")


data = mixture.DataSet()
data.fromArray(mix)

# start them off with something arbitrary (probably based on a guess from the figure)
n1 = mixture.NormalDistribution(-1,1)
n2 = mixture.NormalDistribution(1,1)
m = mixture.MixtureModel(2,[0.5,0.5], [n1,n2])

# perform expectation maximization
m.EM(data, 40, .1)
print m

