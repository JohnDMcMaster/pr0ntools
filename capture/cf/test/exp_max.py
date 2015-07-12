import numpy as np
import scipy as sp
import scipy.stats as ss
import pylab as py
import math
from numpy import random
 
from scipy.stats import expon
 
def generate_population(mu, N=1000, max_sigma=0.5, mean_sigma=0.08):
  """Extract samples from a normal distribution
  with variance distributed as an exponetial distribution
  """
  exp_min_size = 1./max_sigma**2
  exp_mean_size = 1./mean_sigma**2
  sigma = 1/np.sqrt(expon.rvs(loc=exp_min_size, scale=exp_mean_size, size=N))
  return np.random.normal(mu, scale=sigma, size=N), sigma
 
def pdf_model(x, p):
  mu1, sig1, mu2, sig2, pi_1 = p
  return pi_1*py.normpdf(x, mu1, sig1) + (1-pi_1)*py.normpdf(x, mu2, sig2)
 
# generate data from 2 different distributions
N = 60
a = 0.45
m1 = 0.5         # true mean 1 this is what we want to guess
m2 = 3.3       # true mean 2 this is what we want to guess
s1, sig1 = generate_population(m1, N=N*a)
s2, sig2 = generate_population(m2, N=N*(1-a))
s = np.concatenate([s1, s2])   # put all together
sigma_tot = np.concatenate([sig1, sig2])
 
#py.hist(s, bins=np.r_[-1:2:0.025], alpha=0.3, color='g', histtype='stepfilled');
ax = py.twinx(); ax.grid(False)
ax.plot(s, 0.1/sigma_tot, 'o', mew=0, ms=6, alpha=0.4, color='b')
#py.xlim(-0.5, 1.5)
py.title('Sample to be fitted')
 
py.show()
 
# Initial guess of parameters and initializations
p0 = np.array([-0.2, 0.2, 0.8, 0.2, 0.5])
mu1, sig1, mu2, sig2, pi_1 = p0
mu = np.array([mu1, mu2]) # estimated means
sig = np.array([sig1, sig2]) # estimated std dev
pi_ = np.array([pi_1, 1-pi_1]) # mixture parameter
 
gamma = np.zeros((2, s.size))
N_ = np.zeros(2)
p_new = p0
 
# EM we start here
delta = 0.000001
improvement = float('inf')
 
counter = 0
 
while (improvement>delta):
    # Compute the responsibility func. and new parameters
    for k in [0,1]:
        gamma[k,:] = pi_[k]*py.normpdf(s, mu[k], sig[k])/pdf_model(s, p_new)   # responsibility

        N_[k] = 1.*gamma[k].sum() # effective number of objects to k category
        mu[k] = sum(gamma[k]*s)/N_[k] # new sample mean of k category
        sig[k] = np.sqrt( sum(gamma[k]*(s-mu[k])**2)/N_[k] ) # new sample var of k category
        pi_[k] = N_[k]/s.size # new mixture param of k category
        # updated parameters will be passed at next iter
        p_old = p_new
        p_new = [mu[0], sig[0], mu[1], sig[1], pi_[0]]
        # check convergence
        improvement = max(abs(p_old[0] - p_new[0]), abs(p_old[1] - p_new[1]) )
        counter += 1
 
print "Means: %6.3f %6.3f" % (p_new[0], p_new[2])
print "Std dev: %6.3f %6.3f" % (p_new[1], p_new[3])
print "Mix (1): %6.3f " % p_new[4]
print "Total iterations %d" % counter
print pi_.sum(), N_.sum()

