# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
import re

# #add the required path for geomeppy special branch
#add the reauired path for all the above folder
MUBES_Paths = os.path.normcase(os.path.join(os.path.dirname(os.path.dirname(os.getcwd())), 'mubes-ubem'))
sys.path.append(MUBES_Paths)

import TestMakeUpperTower as MakeTower
import pyswarm
from subprocess import check_call

#this function will launch the optimization pso  algorithm.
#lets first get the playground : base of building that will have an upper tower to be tuned
PlayGround = MakeTower.getBasePlayGround()
BldIndex = {}
for ídxe,key in enumerate(PlayGround.keys()):
    BldIndex[ídxe] = key


def grabParameters(x):
    nbBase = int(len(x) / 6)
    param = {}
    for base in range(nbBase):
        param[base] = {}
        param[base]['xc'] = x[0+6*base]
        param[base]['yc'] = x[1+6*base]
        param[base]['angle'] = x[2+6*base]
        param[base]['area'] = x[3+6*base]
        param[base]['shapeF'] = x[4+6*base]
        param[base]['height'] = x[5+6*base]
    return param

def constraints(x,*args):
    #this function gives the constraints to each parameter to be tuned
    #variable have their own limits given in the bounds
    #other constraints can be given here as function using the global vector of parameter x
    #the first constraint is thet the tower should fully stand on the base
    #(x, y, angle, area, shapeFactor, height)
    param = grabParameters(x)
    TowerOK = {}

    for base in param.keys():
        TowerOK[base] = MakeTower.checkTower(PlayGround[BldIndex[base]], x=param[base]['xc'], y=param[base]['yc'],
                                             height=param[base]['height'],area=param[base]['area'],
                                                shapeF=param[base]['shapeF'], angle=param[base]['angle'])
    #TowerOK should all be True and only True
    print([val for val in TowerOK if TowerOK[val]==True])
    Towertest = sum([-1000 if TowerOK[val] == False else 1 for val in TowerOK])

    #another constraint would be that the hieght shall a multiple of 3
    # to be implemented later !
    return [Towertest]

def CostFunction(x,*args):
    # this cost function consists in launching MUBES for the entire set of buildings,
    # grab the results afterward and compute the total energy needs at the district scale and the solar radiation from
    # window in total and for each building
    # the x vectore consist in all the paremter specified to be tuned.
    # the first thing is to compute the new tower out if these
    # with runMUBES.py, the entire geojson file given will be considered and extra tower from the UpperTowerfile compute
    if constraints(x, *args)[0] <0:
        return 1e9
    print('Youhou')
    param = grabParameters(x)
    UpperTower = {}
    for base in param.keys():
        UpperTower[BldIndex[base]] = MakeTower.checkTowerLocation(PlayGround[BldIndex[base]], x=param[base]['xc'],
                                            y=param[base]['yc'],height=param[base]['height'],area=param[base]['area'],
                                                shapeF=param[base]['shapeF'], angle=param[base]['angle'])
    MakeTower.SaveAndWriteNew(PlayGround,UpperTower)
    cmd = ['python']
    cmd.append(os.path.join(MUBES_Paths,'ModelerFolder','runMUBES.py'))
    check_call(cmd, cwd=os.path.join(MUBES_Paths,'ModelerFolder'))



def main():
    #x,y,angle,height,area and shape factore are to be tuned for each futur tower
    #x,y are the tower centroid coordinates, area and shape factor will then define the rectangle footprint, angle enable to rotate the tower on the base. height is the tower height
    #so each tower gets 6 parameters to tune with lower bound and higher bounds
    #x and y are normalized to be in  [0,1], a function will define is the tower stand fully within the base it will be in the constraints function
    #angle is in [0,89] as the shape factor considers higher angle of rotation : shape foctor = 5 <==> shapefactor = 0.2 with 90 of angle rotation
    #height, area and shape factor are given specifically for each building. by default shape factore is between [0.2,5]
    ##
    #all parameter are supposed to be in a single vector of variable, thus the vector will be organize as follow :
    # the order of the play ground defines the vector order by set of 6 parameter for each (x,y,angle,area,shapeFactor,height)
    lowerBounds = []
    upperBounds = []
    for key in BldIndex.keys():
        #for x
        lowerBounds.append(PlayGround[BldIndex[key]]['DistLim'])
        upperBounds.append(1-PlayGround[BldIndex[key]]['DistLim'])
        #for y
        lowerBounds.append(PlayGround[BldIndex[key]]['DistLim'])
        upperBounds.append(1-PlayGround[BldIndex[key]]['DistLim'])
        #for angle
        lowerBounds.append(0)
        upperBounds.append(89)
        #for area
        lowerBounds.append(300)#PlayGround[BldIndex[key]]['minFootprint_m2'])
        upperBounds.append(400) #PlayGround[BldIndex[key]]['maxFootprint_m2'])
        #for ShapeFactor
        lowerBounds.append(0.99)
        upperBounds.append(1)
        # for height
        lowerBounds.append(PlayGround[BldIndex[key]]['minHeight'])
        upperBounds.append(PlayGround[BldIndex[key]]['maxHeight'])
    solution = pyswarm.pso(CostFunction,lowerBounds,upperBounds,f_ieqcons=constraints,maxiter = 1000)
    print(solution)

if __name__ == '__main__':
    main()