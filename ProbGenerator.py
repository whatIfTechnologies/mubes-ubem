import numpy as np
import os

def gives1Val(min,max):
    Val = min + (np.random.beta(2, 1.3) * (max - min))
    return Val

def Write2file(val,name):
    with open(name, 'w') as f:
        for item in val:
            f.write("%s\n" % item)

def BuildData(name,min,max):
    #we alsways start on midnight
    nbocc = []
    TsetUp =[]
    TsetLo = []
    FirstDayofWeek = 0 #the foirst day is a Monday
    for i in range(8760):
        HrperDay = i%24                 #this will gives us values between 0 and 24hours
        DayofWeek = int(i % (24 * 7) / 24) + FirstDayofWeek # this will give the day of the week (0 is for Mondays)
        WE = False if DayofWeek < 6 else True  #this will gove a 1 when we are on weekends
        if HrperDay<8 or HrperDay>18 or WE:
            nbocc.append(0)
            TsetUp.append(28)
            TsetLo.append(15)
        else:
            nbocc.append(gives1Val(min,max))
            TsetUp.append(25)
            TsetLo.append(20)
    Write2file(nbocc,os.path.dirname(os.getcwd()) + '\\InputFiles\\' + name)
    Write2file(TsetUp,os.path.dirname(os.getcwd()) + '\\InputFiles\\SetPointUp.txt')
    Write2file(TsetLo,os.path.dirname(os.getcwd()) + '\\InputFiles\\SetPointLo.txt')

#BuildData('Test_fichier.txt',0,10)