from state import StateVector
from utils import randomOrthonormalMatrix
import numpy as np
from numpy.random import rand



class DifferentialActionModelLQR:
  """
  This class implements a linear dynamics, and quadratic costs.
  Since the DAM is a second order system, and the integratedactionmodels are implemented
  as being second order integrators, This class implements a second order linear system
  given by
  x = [q, v]
  
  dv = A v + B q + C u + d  ......A, B, C are constant
  
  Full dynamics:
  [dq] = [0  1][q]  +  [0]
  [ddq]  [B  A][v] +  [C]u + d

  The cost function is given by l(x,u) = x^T*Q*x + u^T*U*u
  """

  def __init__(self,nq,nu):

    self.nq,self.nv = nq, nq
   
    self.nx = 2*self.nq
    self.ndx = self.nx
    self.nout = self.nv
    self.nu = nu
    self.unone = np.zeros(self.nu)
    self.State = StateVector(self.nx)
    self.nx = self.State.nx
    self.ndx = self.State.ndx
    self.nu = nu
    self.unone = np.zeros(self.nu)

    v1 = randomOrthonormalMatrix(self.nq);
    v2 = randomOrthonormalMatrix(self.nq);
    v3 = randomOrthonormalMatrix(self.nq)

    self.Q = randomOrthonormalMatrix(self.nx);
    self.U = randomOrthonormalMatrix(self.nu)

    self.d = rand(self.nv)
    
    self.B = v1; self.A = v2; self.C = v3

    

  def createData(self): return DifferentialActionDataLQR(self)
  def calc(model,data,x,u=None):
    q = x[:model.nq]; v = x[model.nq:]
    data.xout[:] = (np.dot(model.A, v) + np.dot(model.B, q) + np.dot(model.C, u)).flat + model.d
    data.cost = np.dot(x, np.dot(model.Q, x)) + np.dot(u, np.dot(model.U, u))
    return data.xout, data.cost
  
  def calcDiff(model,data,x,u=None,recalc=True):
    if u is None: u=model.unone
    if recalc: xout,cost = model.calc(data,x,u)
    data.Lx[:] = np.dot(x.T, data.Lxx)
    data.Lu[:] = np.dot(u.T, data.Luu)
    return data.xout,data.cost

class DifferentialActionDataLQR:
  def __init__(self,model):
    self.cost = np.nan
    self.xout = np.zeros(model.nout)
    nx,nu,ndx,nq,nv,nout = model.nx,model.nu,model.State.ndx,model.nq,model.nv,model.nout
    self.F = np.zeros([ nout,ndx+nu ])
    self.Fx = self.F[:,:ndx]
    self.Fu = self.F[:,-nu:]
    
    self.Fx[:,:model.nv] = model.B
    self.Fx[:,model.nv:] = model.A
    self.Fu[:,:] = model.C
    
    self.g = np.zeros( ndx+nu)
    self.L = np.zeros([ndx+nu,ndx+nu])
    self.Lx = self.g[:ndx]
    self.Lu = self.g[ndx:]
    self.Lxx = self.L[:ndx,:ndx]
    self.Lxu = self.L[:ndx,ndx:]
    self.Luu = self.L[ndx:,ndx:]

    self.Lxx = model.Q+model.Q.T
    self.Lxu = np.zeros((nx, nu))
    self.Luu = model.U+model.U.T
        

class DifferentialActionModelNumDiff:
    def __init__(self,model,withGaussApprox=False):
        self.model0 = model
        self.nx = model.nx
        self.ndx = model.ndx
        self.nout = model.nout
        self.nu = model.nu
        self.nq = model.nq
        self.nv = model.nv
        self.State = model.State
        self.disturbance = 1e-5
        try:
            self.ncost = model.ncost
        except:
            self.ncost = 1
        self.withGaussApprox = withGaussApprox
        assert( not self.withGaussApprox or self.ncost>1 )

    def createData(self):
        return DifferentialActionDataNumDiff(self)
    def calc(model,data,x,u): return model.model0.calc(data.data0,x,u)
    def calcDiff(model,data,x,u,recalc=True):
        xn0,c0 = model.calc(data,x,u)
        h = model.disturbance
        dist = lambda i,n,h: np.array([ h if ii==i else 0 for ii in range(n) ])
        Xint  = lambda x,dx: model.State.integrate(x,dx)
        for ix in range(model.ndx):
            xn,c = model.model0.calc(data.datax[ix],Xint(x,dist(ix,model.ndx,h)),u)
            data.Fx[:,ix] = (xn-xn0)/h
            data.Lx[  ix] = (c-c0)/h
            if model.ncost>1: data.Rx[:,ix] = (data.datax[ix].costResiduals-data.data0.costResiduals)/h
        if u is not None:
            for iu in range(model.nu):
                xn,c = model.model0.calc(data.datau[iu],x,u+dist(iu,model.nu,h))
                data.Fu[:,iu] = (xn-xn0)/h
                data.Lu[  iu] = (c-c0)/h
                if model.ncost>1: data.Ru[:,iu] = (data.datau[iu].costResiduals-data.data0.costResiduals)/h
        if model.withGaussApprox:
            data.Lxx[:,:] = np.dot(data.Rx.T,data.Rx)
            data.Lxu[:,:] = np.dot(data.Rx.T,data.Ru)
            data.Lux[:,:] = data.Lxu.T
            data.Luu[:,:] = np.dot(data.Ru.T,data.Ru)

class DifferentialActionDataNumDiff:
    def __init__(self,model):
        nx,ndx,nu,ncost = model.nx,model.ndx,model.nu,model.ncost
        self.data0 = model.model0.createData()
        self.datax = [ model.model0.createData() for i in range(model.ndx) ]
        self.datau = [ model.model0.createData() for i in range(model.nu ) ]

        ndx,nu,nout = model.ndx,model.nu,model.nout

        self.g  = np.zeros([ ndx+nu ])
        self.F  = np.zeros([ nout,ndx+nu ])
        self.Lx = self.g[:ndx]
        self.Lu = self.g[ndx:]
        self.Fx = self.F[:,:ndx]
        self.Fu = self.F[:,ndx:]
        if model.ncost >1 :
            self.costResiduals = self.data0.costResiduals
            self.R  = np.zeros([model.ncost,ndx+nu])
            self.Rx = self.R[:,:ndx]
            self.Ru = self.R[:,ndx:]
        if model.withGaussApprox:
            self. L = np.zeros([ ndx+nu, ndx+nu ])
            self.Lxx = self.L[:ndx,:ndx]
            self.Lxu = self.L[:ndx,ndx:]
            self.Lux = self.L[ndx:,:ndx]
            self.Luu = self.L[ndx:,ndx:]
