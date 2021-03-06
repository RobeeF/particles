#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" 
Illustrate how dimension affects performance of SQMC, by comparing four 
algorithms: 

    * bootstrap SMC
    * bootstrap SQMC
    * guided SMC
    * guided SQMC 

applied to a certain class of Linear Gaussian models. 

For more details, see either:

Chopin, N. and Gerber, M. (2018) Sequential quasi-Monte Carlo: Introduction for
Non-Experts, Dimension Reduction, Application to Partly Observed Diffusion
Processes. arXiv:1706.05305 (to be published in the MCQMC 2016 proceedings). 

or the numerical section of Chapter 12 (SQMC) of the book, where this 
violin plot is reproduced. 

"""

from __future__ import division, print_function

from collections import OrderedDict
from matplotlib import pyplot as plt 
import numpy as np
import pandas as pd 
import seaborn as sb
from scipy import stats

import particles
from particles import state_space_models as ssm 

#parameter values 
alpha0 = 0.4
T = 50
dims = range(5, 21, 5)

# instantiate models 
models = OrderedDict()
true_loglik, true_filt_means = {}, {}
for d in dims: 
    my_ssm = ssm.MVLinearGauss_Guarniero_etal(alpha=alpha0, dx=d)
    _, data = my_ssm.simulate(T)
    truth = my_ssm.kalman_filter(data)
    true_loglik[d] = truth.logpyts.cumsum()
    true_filt_means[d] = truth.filt.means
    models['boot_%i' % d] = ssm.Bootstrap(ssm=my_ssm, data=data)
    models['guided_%i' % d] = ssm.GuidedPF(ssm=my_ssm, data=data)

# Get results 
N = 10**4 
results = particles.multiSMC(fk=models, qmc=[False, True], N=N, moments=True,
                          nruns=100, nprocs=0) 

# Format results 
results_mse = []
for d in dims: 
    for t in range(T): 
        # this returns the estimate of E[X_t(1)|Y_{0:t}]
        estimate = lambda r: r['output'].summaries.moments[t]['mean'][0] 
        for type_fk in ['guided', 'boot']:
            for qmc in [False, True]:  
                est = np.array( [estimate(r) for r in results 
                                 if r['qmc']==qmc and r['fk']==type_fk+'_%i'%d] )
                if type_fk=='guided' and qmc==False: #reference category
                    base_mean = np.mean(est)
                    base_mse = np.var(est)
                else: 
                    mse = np.mean((est-base_mean)**2)
                    log10_gain = -np.log10(mse) + np.log10(base_mse)
                    results_mse.append( {'fk':type_fk, 'dim':d, 'qmc':qmc, 't':t,
                                         'log10_gain':log10_gain} )
# turn it into a pandas DataFrame 
df = pd.DataFrame(results_mse)
df['fk_qmc'] = df['fk'] + df['qmc'].map({True:' SQMC', False:' SMC'})

# Plot
# ====
savefigs = False  # change this to save figs as PDFs
plt.rc('text', usetex=True) #to force tex rendering 

plt.figure()
sb.set_style('darkgrid') #, {'axes.labelcolor': '.05'}) 
sb.set(font_scale=1.3)
plt.axhline(y=0., color='black', lw=2, zorder=0.8) # why 0.8, why? 
ax = sb.violinplot(x="dim", y="log10_gain", hue="fk_qmc", data=df, 
        hue_order=["boot SMC", "boot SQMC", "guided SQMC"],
        palette=sb.light_palette('black', 3, reverse=False))
plt.xlabel('dim')
plt.ylabel(r'gain for $E[X_t(1)|Y_{0:t}]$')
plt.legend(loc=1)
ylabels = ax.get_yticks().tolist()
ax.set_yticklabels([r'$10^{%d}$'%int(i) for i in ylabels])
if savefigs:
    plt.savefig('sqmc_as_dim_grows.pdf') 

plt.show()
