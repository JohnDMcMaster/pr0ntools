# http://stackoverflow.com/questions/10143905/python-two-curve-gaussian-fitting-with-non-linear-least-squares

if 0:
    from sklearn import mixture
    import matplotlib.pyplot
    import matplotlib.mlab
    import numpy as np
    #clf = mixture.GMM(n_components=2, covariance_type='full')
    clf = mixture.GMM(n_components=2)
    clf.fit(yourdata)
    m1, m2 = clf.means_
    w1, w2 = clf.weights_
    c1, c2 = clf.covars_
    histdist = matplotlib.pyplot.hist(yourdata, 100, normed=True)
    plotgauss1 = lambda x: plot(x,w1*matplotlib.mlab.normpdf(x,m1,np.sqrt(c1))[0], linewidth=3)
    plotgauss2 = lambda x: plot(x,w2*matplotlib.mlab.normpdf(x,m2,np.sqrt(c2))[0], linewidth=3)
    plotgauss1(histdist[1])
    plotgauss2(histdist[1])

if 1:
    import numpy as np
    from scipy.optimize import leastsq
    import matplotlib.pyplot as plt

    ######################################
    # Setting up test data
    def norm(x, mean, sd):
      norm = []
      for i in range(x.size):
        norm += [1.0/(sd*np.sqrt(2*np.pi))*np.exp(-(x[i] - mean)**2/(2*sd**2))]
      return np.array(norm)

    mean1, mean2 = 0, -2
    std1, std2 = 0.5, 1 

    x = np.linspace(-20, 20, 500)
    y_real = norm(x, mean1, std1) + norm(x, mean2, std2)

    ######################################
    # Solving
    m, dm, sd1, sd2 = [5, 10, 1, 1]
    p = [m, dm, sd1, sd2] # Initial guesses for leastsq
    y_init = norm(x, m, sd1) + norm(x, m + dm, sd2) # For final comparison plot

    def res(p, y, x):
        m, dm, sd1, sd2 = p
        m1 = m
        m2 = m1 + dm
        y_fit = norm(x, m1, sd1) + norm(x, m2, sd2)
        err = y - y_fit
        return err

    # The actual optimizer
    plsq = leastsq(res, p, args = (y_real, x))

    y_est = norm(x, plsq[0][0], plsq[0][2]) + norm(x, plsq[0][0] + plsq[0][1], plsq[0][3])

    plt.plot(x, y_real, label='Real Data')
    plt.plot(x, y_init, 'r.', label='Starting Guess')
    plt.plot(x, y_est, 'g.', label='Fitted')
    plt.legend()
    plt.show()

