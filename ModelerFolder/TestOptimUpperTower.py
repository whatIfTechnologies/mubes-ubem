# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
import re
import math
import json
import numpy as np
import copy
import shutil
# #add the required path for geomeppy special branch
#add the reauired path for all the above folder
MUBES_Paths = os.path.normcase(os.path.join(os.path.dirname(os.path.dirname(os.getcwd())), 'mubes-ubem'))
sys.path.append(MUBES_Paths)
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)

# import TestMakeUpperTower as MakeTower
import pyswarm
from subprocess import check_call
import ReadResults.Utilities as Utilities

#this function will launch the optimization pso  algorithm.
#lets first get the playground : base of building that will have an upper tower to be tuned
file = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\mubes-ubem\\ModelerFolder\\UpperTower.pickle'
import pickle
with open(file, 'rb') as handle:
    PlayGround = pickle.load(handle)


#PlayGround = MakeTower.getBasePlayGround()
BldIndex = {}
for ídxe,key in enumerate(PlayGround.keys()):
    BldIndex[ídxe] = key

def SaveAndWriteNew(Matches,Towers):
    for key in Matches.keys():
        Matches[key]['UpperTower'] = Towers[key]
    print('\nAll building treated')
    for key in Matches.keys():
        del Matches[key]['Space']
        del Matches[key]['SpaceNew']
    j = json.dumps(Matches)
    with open(os.path.join(MUBES_Paths,'ModelerFolder','UpperTower.json'), 'w') as f:
        f.write(j)


def grabParametersnew(x):
    nbBase = int(len(x) / 5)
    param = {}
    for base in range(nbBase):
        param[base] = {}
        param[base]['height'] = x[0+5*base]
        param[base]['area'] = x[1+5*base]
        param[base]['shapeF'] = x[2+5*base]
        param[base]['angle'] = x[3+5*base]
        param[base]['loc'] = x[4+5*base]
    return param

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

def constraints(x):
    #this function gives the constraints to each parameter to be tuned
    #variable have their own limits given in the bounds
    #other constrains can be given here as function using the global vector of parameter x
    #the below proposed constrain is to be above a minimum of total floor are
    # the value if 110 000 square meter is proposed (to host at least 1000 family)
    #as tower can have different height, the constrains is expresse on a volume of 3*110 000 cube meter
    #more should also lead to more shadowing effect,so we'llk see how the process is optimised
    param = grabParameters(x)
    TowerOK = {}
    totVol = 0
    for base in param.keys():
        height = round(param[base]['height'] / 3, 0)
        area = getTheClosestFromDict(param[base]['area'], PlayGround[BldIndex[base]]['SpaceNew'])
        totVol += height*area
    return [totVol-3*250000]

def check4Values(Bld):
    values = list(Bld.keys())
    valuesCheck = [0]*len(values)
    for validx,val in enumerate(values):
        if type(Bld[val]) == dict and not valuesCheck[validx]:
            for key in Bld[val].keys():
                if type(Bld[val][key]) == dict and not valuesCheck[validx]:
                    for subkey in Bld[val][key].keys():
                        if Bld[val][key][subkey]:
                            valuesCheck[validx] = True
                            break
                else:
                    if Bld[val][key] or valuesCheck[validx]:
                        valuesCheck[validx]  = True
                        break
        else:
            if Bld[val] and not valuesCheck[validx]:
                valuesCheck[val]  = True
    return [val for idx,val in enumerate(values) if valuesCheck[idx]]


def getTheClosestFromDict(var,Bld):
    if type(Bld)==dict:
        values = check4Values(Bld)
    else:
        values = list(np.linspace(0,len(Bld)-1,len(Bld)))
    valmin = min(values)
    valmax = max(values)
    exactval = valmin+var*(valmax-valmin)
    valdiff = [abs(val-exactval) for val in values]
    return values[valdiff.index(min(valdiff))]


def CostFunction(x):
    # this cost function consists in launching MUBES for the entire set of buildings,
    # grab the results afterward and compute the total energy needs at the district scale and the solar radiation from
    # window in total and for each building
    # the x vectore consist in all the paremter specified to be tuned.
    # the first thing is to compute the new tower out if these
    # with runMUBES.py, the entire geojson file given will be considered and extra tower from the UpperTowerfile compute
    currentPath = os.getcwd()
    param = grabParametersnew(x)
    UpperTower = {}
    totVol = 0
    for base in param.keys():
        #lets fod the closest surface first
        height = round(param[base]['height']/3,0)
        area = getTheClosestFromDict(param[base]['area'],PlayGround[BldIndex[base]]['SpaceNew'])
        ShapeFact = getTheClosestFromDict(param[base]['shapeF'],PlayGround[BldIndex[base]]['SpaceNew'][area])
        angle = getTheClosestFromDict(param[base]['angle'],PlayGround[BldIndex[base]]['SpaceNew'][area][ShapeFact])
        locidx = getTheClosestFromDict(param[base]['loc'],PlayGround[BldIndex[base]]['SpaceNew'][area][ShapeFact][angle])
        loc = PlayGround[BldIndex[base]]['SpaceNew'][area][ShapeFact][angle][int(locidx)]
        UpperTower[BldIndex[base]] = checkTowerLocation(PlayGround[BldIndex[base]], x=loc[0]/100,y=loc[1]/100,
                                            height=height,area=area,shapeF=ShapeFact, angle=angle*10)
        totVol += area * height
    SaveAndWriteNew(copy.deepcopy(PlayGround),UpperTower)
    globResPath = os.path.join(os.path.dirname(MUBES_Paths), 'MUBES_SimResults', 'OptimShadowRes')
    liste = os.listdir(globResPath)
    nbfile = 0
    for file in liste:
        if file[-5:] == '.json':
            nbfile += 1
    CaseName = 'OptimShadow'+str(nbfile)
    cmdline = [
        os.path.abspath('C:/Users/xav77/Envs/MUBES_UBEM/Scripts/python.exe'),
        os.path.join(MUBES_Paths,'ModelerFolder','runMUBES.py')
    ]
    cmdline.append('-CONFIG')
    cmdline.append('''{"1_DATA": {"PATH_TO_DATA": "C:/Users/xav77/Documents/FAURE/DataBase/Noah/markham_v3_core_v6_no-towers.geojson"},
            "2_CASE": {"0_GrlChoices": { "CaseName": "OptimShadow","Verbose" : false,"DebugMode": false},"2_AdvancedChoices": {"ExtraTowerFile":
            "''' + str(os.path.join(MUBES_Paths,'ModelerFolder','UpperTower.json')).replace('\\', '/') + '"}},"3_SIM": {"1_WeatherData": {"WeatherDataFile":\
            "WeatherData/CAN_ON_Toronto.716240_CWEC.epw", "Latitude": 43.67,"Longitude": -79.63,"Time_Zone": -5.0,"Elevation": 173.0}}}''')
    check_call(cmdline, cwd=os.path.join(MUBES_Paths,'ModelerFolder'))
    Res_Path = os.path.join(os.path.dirname(MUBES_Paths),'MUBES_SimResults','OptimShadow','Sim_Results')
    extraVar = ['HeatedArea'] #some toher could be added for the sake fo cost_function
    Res = Utilities.GetData(Res_Path, extraVar)
    TotalSolar = 0
    for bld in Res['HeatedArea']:
        TotalSolar += sum(bld['Data_Surface Outside Face Incident Beam Solar Radiation Rate per Area'])
    globalCostVar = 1e9/(TotalSolar)
    shutil.copyfile(os.path.join(MUBES_Paths,'ModelerFolder','UpperTower.json'), os.path.join(globResPath,'UpperTower'+str(nbfile)+'.json'))
    shutil.copyfile(os.path.join(MUBES_Paths, 'ModelerFolder', 'GlobGeoJsonImage.png'),os.path.join(globResPath, 'UpperTower' + str(nbfile) + '.png'))
    with open(os.path.join(globResPath,'CostFunctionRes.txt'), 'a') as f:
        f.write(str(globalCostVar)+'\t'+str(totVol)+'\n')
    os.chdir(currentPath)
    return globalCostVar

def makeimage():
    globResPath = os.path.join(os.path.dirname(MUBES_Paths), 'MUBES_SimResults', 'OptimShadowRes')
    liste = os.listdir(globResPath)
    nbfile = 0
    for file in liste:
        if file[-5:] == '.json':
            nbfile += 1
    for i in range(nbfile):
        cmdline = [
            os.path.abspath('C:/Users/xav77/Envs/MUBES_UBEM/Scripts/python.exe'),
            os.path.join(MUBES_Paths, 'ModelerFolder', 'runMUBES.py')
        ]
        cmdline.append('-CONFIG')
        cmdline.append('''{"1_DATA": {"PATH_TO_DATA": "C:/Users/xav77/Documents/FAURE/DataBase/Noah/markham_v3_core_v6_no-towers.geojson"},
        "2_CASE": {"0_GrlChoices": { "CaseName": "ForImages","MakePlotsOnly": true,"Verbose" : false,"DebugMode": false},"2_AdvancedChoices": {"ExtraTowerFile":
        "'''+str(os.path.join(globResPath,'UpperTower'+str(i)+'.json')).replace('\\','/')+'"}}}''')
        check_call(cmdline, cwd=os.path.join(MUBES_Paths, 'ModelerFolder'))
        shutil.copyfile(os.path.join(MUBES_Paths,'ModelerFolder','GlobGeoJsonImage.png'), os.path.join(globResPath,'UpperTower'+str(i)+'.png'))

def makeMovie():
    globResPath = os.path.join(os.path.dirname(MUBES_Paths), 'MUBES_SimResults', 'OptimShadowRes')
    import moviepy.video.io.ImageSequenceClip
    image_folder = 'folder_with_images'
    fps = 5

    image_files = [os.path.join(image_folder, img)
                   for img in os.listdir(image_folder)
                   if img.endswith(".png")]
    clip = moviepy.video.io.ImageSequenceClip.ImageSequenceClip(image_files, fps=fps)
    clip.write_videofile('my_video.mp4')

def checkTowerLocation(Bld,x=0.5,y=0.5,height=9,area=500,shapeF = 2,angle = 0):
    X,Y = makeGlobCoord(x,y,Bld) #centroid of the tower on the base
    #make the square shape
    #it requires a bounds for a shape factor (lets use 0.2 and 5, with a minimum of 5m for smallest edge length)
    #these should be given in the geojson file as can be specific to the building
    #computing the length of the edges
    edge1 = (area/shapeF)**0.5
    edge2 = edge1*shapeF
    Coord = [(-edge1/2,-edge2/2),(-edge1/2,edge2/2),(edge1/2,edge2/2),(edge1/2,-edge2/2)]
    Coord = [(rotateCoord(node,angle)) for node in Coord]
    TowerCoord = [(node[0]+X,node[1]+Y) for node in Coord]
    return  {'Coord' : TowerCoord, 'Height' : height}

def rotateCoord(node,angle):
    X = node[0] * math.cos(math.radians(angle)) - node[1] * math.sin(math.radians(angle))
    Y = node[0] * math.sin(math.radians(angle)) + node[1] * math.cos(math.radians(angle))
    return X,Y

def makeGlobCoord(x,y,Bld):
    # lets transform x and y into global coordinates
    # get x and y with value sized to the figure
    x = x * Bld['EdgeLength'][0]
    y = y * Bld['EdgeLength'][1]
    # rotation transformation
    X,Y = rotateCoord((x, y), Bld['RefAngle'])
    #translation transformation
    X += Bld['Origin'][0]
    Y += Bld['Origin'][1]
    return (X,Y)

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
        lowerBounds.append(PlayGround[BldIndex[key]]['minHeight'])
        upperBounds.append(PlayGround[BldIndex[key]]['maxHeight'])
        for i in range(4):
        #for all parameters the 5 variables are :
        # the order is :
        #height, area, shape factor, angle, tuple of coordinates
        # all are normalized between 0 and 1
            lowerBounds.append(0)
            upperBounds.append(1)
    solution = pyswarm.pso(CostFunction,lowerBounds,upperBounds,f_ieqcons=constraints,maxiter = 1000)
    #solution = pyswarm.pso(CostFunction, lowerBounds, upperBounds, maxiter=1000)
    print(solution)

if __name__ == '__main__':
    main()
    makeMovie()