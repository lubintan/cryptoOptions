from scipy.stats import norm
import numpy as np

from okexAPI import *

class IV:

    def __init__(self, S0=0, Sk=0, r=0, t=0, sig=0):

        self.S0 = S0
        self.Sk = Sk
        self.r = r
        self.t = t
        self.sig = sig
        self.d1Val = None
        self.d2Val = None

    def setSig(self,sig):
        self.sig = sig

    def getVal(self, input):
        return norm.cdf(input)

    def d1(self):
        a = np.log(self.S0/self.Sk)
        b = (self.r + ((self.sig ** 2)/2)) * self.t
        c = self.sig * ( self.t ** 0.5)
        self.d1Val = (a + b) / c
        return self.d1Val

    def d2(self):
        # if self.d1Val != None:
        #     self.d2Val = self.d1Val - (self.sig * (self.t ** 0.5))
        # else:
        a = np.log(self.S0 / self.Sk)
        b = (self.r - ((self.sig ** 2) / 2)) * self.t
        c = self.sig * (self.t ** 0.5)
        self.d2Val = (a + b) / c
        return self.d2Val

    def c(self,r):
        self.r = r
        # if self.d1Val == None:
        #     self.d1()
        # if self.d2Val == None:
        #     self.d2()

        a = self.S0 * norm.cdf(self.d1())
        b = self.Sk * (np.e ** (-1 * self.r * self.t)) * norm.cdf(self.d2())

        return a - b


def getCallProb(s0, sk, sig,t):
    a = norm.cdf((np.log(sk/s0)) / (sig * np.sqrt(t)) )

    return 1-a



def okexCalls():

    apiKey = open('api.key','r').read()
    otherKey = open('other.key','r').read()
    ppKey = open('pp.key','r').read()

    ok = Okex(apiKey,otherKey,ppKey,'')
    res = ok.options('200515','10000','C')

    for r in res:
        print(r, res[r])



if __name__ == '__main__':



    okexCalls()
    exit()


    btcPrices=[7504, 7529.3,7544.9,7674.4,7716.7,8358.9,8777.2,8727.9,8936.9,8814.1,8846.9,8843.8,9273.5,9516.3]
    # btcPrices.pop(0)

    btcPrices = btcPrices[-7:]
    print(len(btcPrices))

    v = np.std(btcPrices)

    v1 = v
    v2 = v

    May8Settlemet = 9786

    s0 = 9600

    strike1 = 9000
    strike2 = 9750

    t = 1/365

    p1 = getCallProb(s0, strike1,v1,t)
    p2 = getCallProb(s0, strike2,v2,t)

    print(p1, p2)

    left = 1-p1
    right = p2

    print(1-left-right)

    left = 1-0.82
    right = 0.22
    print(1 - left - right)

    L2 = .71
    R2 = .48

    left = 1 - L2
    right = R2

    print(1 - left - right)




    # print(v)




    exit()

    iv = IV(
        S0 = 9958.83,
        Sk = 10000,
        r = None,
        t = 7/365,
        sig = .7714
    )

    # print(0.1118*9958.83, 0.1085*9958.83)

    while True:

        r = float(input('r:'))
        print(iv.c(r))
        print(iv.d1())

    #

    # Rs = range(1,3000)
    # Cs = []
    # for each in Rs:
    #     rrr = each * 0.001
    #     iv.setSig(rrr)
    #
    #     c = iv.c()
    #
    #     if len(Cs) > 1 and c < Cs[-1]:
    #         print(rrr, "Error!!")
    #         exit()
    #
    #     Cs.append(iv.c())
    #
    #
    #     print('%.5f  | %.5f'%(rrr, Cs[-1]))


    # # print(iv.d1(), iv.d2())
    # print(iv.c())
    # # print(norm.cdf(-.6278))



