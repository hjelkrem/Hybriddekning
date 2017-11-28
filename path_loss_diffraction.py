import numpy as np

def path_loss(di,hi,hts,hrs,f):
    #Parameters
    ae=8500 #Equivalent Earth radius
    Ce=1./ae # Equivalent Earth curvature
    lam=3.0*10**8/f  # wave length
    N=di.size # Length of array
    d=di[-1];
    
    #Free-space path loss
    Lbf=32.4+20*np.log10(f/1e6)+20*np.log10(d)     
    # Diffraction loss
    Ldb=delta_bullington(d,di,hi,hts,hrs,Ce,lam,N)
    # Total path loss
    Ltot=Lbf+Ldb
    return(Ltot)
    
def delta_bullington(d,di,hi,hts,hrs,Ce,lam,N):
    # Diffraction loss actual path
    Lba=std_bullington(d,di,hi,hts,hrs,Ce,lam,N)
    # Diffraction loss smooth spheric Earth
    [Lbs,h1,h2]=std_bullington_smooth(d,di,hi,hts,hrs,Ce,lam,N)
    # Diffraction loss smooth Earth
    Lsph = diff_loss_sph_earth(h1,h2,1./Ce,d,lam)
    # Total diffraction loss
    L=Lba+max(Lsph-Lbs,0)
    return(L)

def std_bullington(d,di,hi,hts,hrs,Ce,lam,N):
    # Calculate slopes
    I=np.arange(1,N-1)
    Stim=(hi[I]+500*Ce*di[I]*(d-di[I])-hts)/di[I]
    Srim=(hi[I]+500*Ce*di[I]*(d-di[I])-hrs)/(d-di[I])
    Str=(hrs-hts)/d
    # Calculate Bullington diffraction loss   
    if np.amax(Stim)<Str:
        corr=np.sqrt(0.002*d/(lam*di[I]*(d-di[I])))
        v=(hi[I]+500*Ce*di[I]*(d-di[I])-(hts*(d-di[I])+hrs*di[I])/d)*corr#eq 51
        vmax=np.amax(v)
        if vmax>-0.78:
            Luc=6.9+20*np.log10(np.sqrt((vmax-0.1)**2+1)+vmax-0.1) # eq.52,31
        else:
            Luc=0
    else:
        db=(hrs-hts+np.amax(Srim)*d)/(np.amax(Stim)+np.amax(Srim)) # eq. 54
        corr=np.sqrt(0.002*d/(lam*db*(d-db)))
        vb=(hts+np.amax(Stim)*db-(hts*(d-db)+hrs*db)/d)*corr  #eq. 55
        if vb>-0.78:
            Luc=6.9+20*np.log10(np.sqrt((vb-0.1)**2+1)+vb-0.1) # eq.56,31
        else:
            Luc=0
    Lb=Luc+(1-np.exp(-Luc/6))*(10+0.02*d) # eq. 57
    return(Lb)

def std_bullington_smooth(d,di,hi,hts,hrs,Ce,lam,N):
    I=np.arange(1,N-1)
    I1=np.arange(1,N)    
    I0=np.arange(0,N-1)    
    v1=np.sum((di[I1]-di[I0])*(hi[I1]+hi[I0])) # eq. 58
    v2=np.sum((di[I1]-di[I0])*(hi[I1]*(2.0*di[I1]+di[I0])+hi[I0]*(di[I1]+2*di[I0]))) # eq. 59
    hstip=(2*v1*d-v2)/d**2 # eq.60a
    hsrip=(v2-v1*d)/d**2 # eq 60b
    hobi=hi[I]-(hts*(d-di[I])+hrs*di[I])/d # eq.61d
    hobs=np.amax(hobi) # eq. 61a
    aobt=np.amax(hobi/di[I]) # eq.61b
    aobr=np.amax(hobi/(d-di[I])) # eq.61c
    if hobs<0.0: 
        hstp=hstip # eq. (62a)
        hsrp=hsrip # eq. (62b)
    else: 
        gt=aobt/(aobt+aobr) # eq.62e
        gr=aobr/(aobt+aobr) # eq. 62f
        hstp=hstip-hobs*gt # eq. 62c
        hsrp=hsrip-hobs*gr # eq.62d
    if hstp>hi[1]:
        hst=hi[1] # eq.63a
    else:
        hst=hstp # eq. (63b)
    if hsrp>hi[N-1]:
        hsr=hi[N-1] # eq. (63c)
    else:
        hsr=hsrp # eq.63d
    h2ts=hts-hst # eq. 64a
    h2rs=hrs-hsr # eq. 64b
    h2i=np.zeros(N)
    Lbs=std_bullington(d,di,h2i,h2ts,h2rs,Ce,lam,N)
    h1=h2ts
    h2=h2rs
    return(Lbs,h1,h2)
    
def diff_loss_sph_earth(h1,h2,ae,d,lam):
    dlos=np.sqrt(2*ae)*(np.sqrt(h1)+np.sqrt(h2)) # eq. 21
    if d>=dlos:
        Lsph= diff_sph_earth(d,h1,h2,ae,3.0e8/lam)
    else: 
        m=d**2/(4*ae*(h1+h2))  # eq. 22e
        c=(h1-h2)/(h1+h2) # eq.22d
        b=2*np.sqrt((m+1)/(3*m)) * np.cos(np.pi/3+1./3*np.arccos(3.0*c/2*np.sqrt(3.0*m/(m+1)**3))) # eq 22c
        d1=d/2*(1+b) # eq. 22a
        d2=d-d1 # eq.22b
        h=((h1-d1**2/(2*ae))*d2+(h2-d2**2/(2*ae))*d1)/d # eq.22
        hreq=0.552*np.sqrt(d1*d2*lam/d)
        if h>hreq:
            Lsph=0
        else:
            aem=0.5*(d*1e3/(np.sqrt(h1)+np.sqrt(h2)))**2 
            Ah=diff_sph_earth(d,h1,h2,aem,3.0e8/lam)
            Lsph=(1-h/hreq)*Ah # eq. 25
    return(Lsph)
            
def diff_sph_earth(d,h1,h2,ae,f):
    X=2.188*(f/1e6)**(1./3)*ae**(-2./3)*d # eq. 14a
    Y1=9.575e-3*(f/1e6)**(2./3)*ae**(-1./3)*h1 # eq. 15a
    Y2=9.575e-3*(f/1e6)**(2./3)*ae**(-1./3)*h2 # eq. 15a
    if X>=1.6:
        FX=11+10*np.log10(X)-17.6*X # eq. 17a
    else:
        FX=-20*np.log10(X)-5.6488*X**1.425 # eq. 17b
    B1=Y1 # eq.18b
    if B1>2:
        GY1=17.6*np.sqrt(B1-1.1)-5*np.log10(B1-1.1)-8 # eq. 18
    else:
        GY1=20*np.log10(B1+0.1*B1**3) # eq. 18a
    B2=Y2 # eq. 18b
    if B2>2:
        GY2=17.6*np.sqrt(B2-1.1)-5*np.log10(B2-1.1)-8
    else:
        GY2=20*np.log10(B2+0.1*B2**3);
    A=-(FX+GY1+GY2); # eq. 13
    return(A)
    

                
            
        
        