from osgeo import osr, gdal, ogr
from qgis.core import *

class RoadPointList:

    def __init__(self, layer):
        #Using a dictionary to store which coordinates have been added to the list.
        #This gives a slight additional memory overhead, but a huge performance boost,
        #as the dictionary checks are O(1).
        self.__contents = {}
        self.list = []

    def addAround(self, sx, sy, radius):
        for x in range(sx - radius, sx + radius):
            for y in range(sy - radius, sy + radius):
                self.add(x, y)

    def addRange(self, list):
        for coord in list:
            self.add(coord[0], coord[1])

    def add(self, sx, sy):
        #Check if this coordinate has been added before, and add it if not.
        isNew = False
        if x not in self.__contents:
            self.__contents[x] = { y: 1}
            isNew = True
        elif y not in self.__contents[x]:
            self.__contents[x][y] = 1
            isNew = True

        if isNew:
            self.list.append((x, y))