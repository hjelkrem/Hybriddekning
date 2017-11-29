# -*- coding: utf-8 -*-
"""
Created on Tue Oct 31 10:16:34 2017

@author: janh
"""
from path_loss_diffraction import *
import numpy as np
import matplotlib.pylab as plt

#Frequency
f=900e6

# Height of antennas
hts0=10 # TX antenna above ground
hrs0=1 # RX antenna above ground


# Make terrain profile
hmax=120 # Max obstruction height
hmin=100 # Min obstruction height
P=1 # Number of periods
dv=np.arange(2,500) # Vector of link length
deltad=1 # Distance between points
N0=dv[-1]/deltad # Number of samples of longest vector
Lv=np.zeros(len(dv)) # Initiating loss vector
#Lbfv=np.zeros(len(dv))
#Ldbv=np.zeros(len(dv))
for i in range(0,len(dv)):
    d=dv[i]
    di=np.arange(0,d+deltad,deltad) # Distance array
    N=di.size # Length of array
    n=np.arange(0,N)
    hi=hmin+(hmax-hmin)*np.sin(2*np.pi*P/N0*n)
    hts=hts0+hi[0] # TX antenna above sea level
    hrs=hrs0+hi[N-1]    # RX antenna above sea level
    L=path_loss(di,hi,hts,hrs,f) # Total path loss
    Lv[i]=L
 #   Lbfv[i]=Lbf
 #   Ldbv[i]=Ldb

plt.clf()
plt.plot(dv,Lv,label='Total')
#plt.plot(dv,Lbfv,label='Free space')
#plt.plot(dv,Ldbv,label='Diffraction')
plt.grid()
plt.xlabel('Distance [km]')
plt.ylabel('Loss [dB]')
#legend=plt.legend(loc='Lower right')
