# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Hybriddekning
                                 A QGIS plugin
 Plugin for assessment of communication technology
                              -------------------
        begin                : 2017-10-19
        git sha              : $Format:%H$
        copyright            : (C) 2017 by SINTEF
        email                : OddAndre.Hjelkrem@sintef.no
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QDate, QSettings, QVariant,QFile, QFileInfo
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QDateEdit, QColor, QFileDialog, QButtonGroup, QProgressBar
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from Hybriddekning_dialog import HybriddekningDialog
from antenna import Antenna
from rasterLayer import RasterLayer
from timing import Timing
from roadPointList import RoadPointList
import multiprocessing
import threading
import os.path
from osgeo import osr, gdal, ogr
from qgis.gui import QgsMessageBar
from qgis.utils import iface
from qgis.core import *
import numpy as np
import scipy.ndimage as ndimage
import matplotlib.pyplot as plt
import time
from path_loss_diffraction import *
import os
from datetime import datetime
from datetime import timedelta

class Hybriddekning:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Hybriddekning_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Hybriddekning')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'Hybriddekning')
        self.toolbar.setObjectName(u'Hybriddekning')

        self.lastTiming = None
        self.timingLog = ""

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Hybriddekning', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = HybriddekningDialog()
        self.dlg.btnBrowseTxt.clicked.connect(self.open_txt_file)

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Hybriddekning/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Hybriddekning'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&Hybriddekning'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def calculate_propagation_np(self,dists,heights,f,ant_h):
        N=dists.size
        hts0=ant_h # TX antenna above ground
        hrs0=1 # RX antenna above ground
        hts=hts0+heights[0] # TX antenna above sea level
        hrs=hrs0+heights[N-1]    # RX antenna above sea level
        signal=path_loss(dists,heights,hts,hrs,f)
        #signal=int(10000000/sum(dist))
        #for element in height_skog:
         #   if element>0:
          #      signal=200
        return signal
        """Runs the propagation model for the selected layers """

    def calculate_propagation(self,dist,height,f,ant_h):
        #f=5900e6
        #height=list(reversed(height))
        #height_skog=list(reversed(height_skog))
        #dist=list(reversed(dist))
        hi=np.array(height)#+np.array(height_skog)
        #self.dprint(str(hi))
        
        di=np.array(dist)
        di=di*0.001
        #self.dprint(str(di))
        N=di.size
        hts0=ant_h # TX antenna above ground
        hrs0=1 # RX antenna above ground
        hts=hts0+hi[0] # TX antenna above sea level
        hrs=hrs0+hi[N-1]    # RX antenna above sea level
        signal=path_loss(di,hi,hts,hrs,f)
        #signal=int(10000000/sum(dist))
        #for element in height_skog:
         #   if element>0:
          #      signal=200
        return signal
        """Runs the propagation model for the selected layers """


    def bilinear(self, x1,x2,y1,y2,x,y,data):
        p=data[y1][x1]*((x2+0.5)-x)*((y2+0.5)-y)+data[y1][x2]*(x-(x1+0.5))*((y2+0.5)-y)+data[y2][x1]*((x2+0.5)-x)*(y-(y1+0.5))+data[y2][x2]*(x-(x1+0.5))*(y-(y1+0.5))
        return p

    def dprint(self,msg):
        QMessageBox.information(self.iface.mainWindow(),"Message",msg)

    def open_txt_file(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select rasterfile to write to", "", "*.tif")
        self.dlg.txtDem.setText(filename)

    def checkCrs(self, layers):
        for i, layer in enumerate(layers):
            if i < 1: continue
            if layer.crs() != layers[i-1].crs():
                s = "The projections of all the layers are not matching!"
                for l in layers:
                    s += "\n" + l.name() + ": " + str(l.crs().authid())
                self.dprint(s)
                return False
        return True

    def printHeightProfile(self):
        
        rasterLayer = self.dlg.getSurfaceLayer()
        #TODO: Use terrain layer too! (self.dlg.getTerrainLayer())
        antennaLayer = self.dlg.getAntennaLayer()

        if rasterLayer is None or antennaLayer is None:
            self.dprint("Not sufficient layers for calculations")
            return

        ants = [x.geometry().asPoint() for x in antennaLayer.selectedFeatures()]
        if len(ants) != 2:
            self.dprint("Too " + ("many" if len(ants) > 2 else "few") + " points! This function needs 2, and you have selected " + str(len(ants)) + ".")
            return

        if not self.checkCrs([rasterLayer, antennaLayer]):
            return

        raster = RasterLayer(rasterLayer)
        cell_size_meters = raster.findCellSizeInMeters()

        filestring = []
        
        point = [self.findcell(ants[0], raster.geotransform), ants[1]]
        xdist, xheight = self.get_heights_along_x(point, raster.geotransform, raster.data, cell_size_meters)
        ydist, yheight = self.get_heights_along_y(point, raster.geotransform, raster.data, cell_size_meters)
        dist, height = self.combine_and_sort(xdist, xheight, ydist, yheight, filestring)
        line = plt.figure()
        
        plt.plot(dist, height)
        
        plt.show()

    def timeit(self, message, reset=False):
        
        if self.lastTiming is None or reset:
            self.lastTiming = datetime.now()

        if reset:
            QgsMessageLog.logMessage(message, "Hybriddekning", 0)
        else:
            delta = datetime.now() - self.lastTiming
            QgsMessageLog.logMessage("    " + message + ": " + str(delta.total_seconds() * 1000), "Hybriddekning", 0)

    def findValidAntennas(self, antennaLayer, geotransform, xmin, xmax, ymin, ymax):
        start_point = QgsPoint(xmin, ymax)
        end_point = QgsPoint(xmax, ymin)
        startcella = self.findcell(start_point, geotransform)
        sluttcella = self.findcell(end_point, geotransform)

        antennas = Antenna.fromFeatures(antennaLayer.getFeatures())
        validAntennas = []

        self.timeit("Antenna area start: " + str(startcella[0]) + ", " + str(startcella[1]))
        self.timeit("Antenna area end: " + str(sluttcella[0]) + ", " + str(sluttcella[1]))

        for ant in antennas:
            ant.qgisPoint = self.findcell(ant.point, geotransform)
            self.timeit("Compared to: " + str(ant.qgisPoint[0]) + ", " + str(ant.qgisPoint[1]))
            self.timeit("Compared to: " + str(ant.qgisPoint[0]) + ", " + str(ant.qgisPoint[1]))
            if ant.qgisPoint[0] > startcella[0] and ant.qgisPoint[0] < sluttcella[0] and ant.qgisPoint[1] > startcella[1] and ant.qgisPoint[1] < sluttcella[1]:
                validAntennas.append(ant)

        return validAntennas

    def calculateSignalAtPoint(self, cellSizeInMeters, surface, terrain, validAntennas, cell):

        foundSignal = False
        minSignal = 999999
        outsideOfRaster = 0
        insideRaster = 0

        for ant in validAntennas:

            points = self.get_cells_Bresenham(cell, ant.qgisPoint)

            if len(points) <= 3: # Not enough points between the start and end points.
                continue

            length = cellSizeInMeters * np.hypot(cell[0] - ant.qgisPoint[0], cell[1] - ant.qgisPoint[1])
            count = len(points)
            std_dist = length / count * 0.001
            heights = np.empty(count)
            dists = np.empty(count)
            accumulatedDist = 0.0

            for i, point in enumerate(points):
                
                firstOrLastPoint = True if i < 1 or i >= len(points) - 1 else False
                heightSource = terrain if firstOrLastPoint else surface
                try:
                    height = heightSource.data[point[1]][point[0]]
                    insideRaster += 1
                except:
                    height = 0
                    outsideOfRaster += 1

                heights[i] = height
                dists[i] = accumulatedDist
                accumulatedDist += std_dist

            result = self.calculate_propagation_np(dists, heights, ant.frequencyHz, ant.height)
            if result > 0 and result < minSignal:
                minSignal = result
                foundSignal = True

        return foundSignal, minSignal, outsideOfRaster, insideRaster

    def getRoadPoints(self, surface, roadLayer, radius):

        roadPoints = RoadPointList()

        for link in roadLayer.selectedFeatures():

            geom = link.geometry().asPolyline()
            startcelle = self.findcell(QgsPoint(geom[0]), surface.geotransform)

            #Find the nearest points
            roadPoints.addAround(startcelle[0], startcelle[1], radius)

            for i in range(1, len(geom)):
                sluttcelle = self.findcell(QgsPoint(geom[i]), surface.geotransform)
                cells = self.get_cells_Bresenham(startcelle, sluttcelle)
                for cell in cells:
                    roadPoints.addAround(cell[0], cell[1], radius)

                startcelle = sluttcelle

        return roadpoints.list

    def getRoadPointsForOptimize(self, surface, roadLayer):

        roadPoint = RoadPointList()

        for link in roadLayer.selectedFeatures():
            
            geom = link.geometry().asPolyline()
            startcelle = self.findcell(QgsPoint(geom[0]), surface.geotransform)

            roadpoints.add(startcelle[0], startcelle[1])

            for i in range(1, len(geom)):
                sluttcelle = self.findcell(QgsPoint(geom[i]), geotransform)
                cells = self.get_cells_Bresenham(startcelle,sluttcelle)
                roadPoints.addRange(cells)
                startcelle = sluttcelle

    def calculateSignal(self):

        surfaceLayer = self.dlg.getSurfaceLayer()
        terrainLayer = self.dlg.getTerrainLayer()
        roadLayer = self.dlg.getRoadLayer()
        antennaLayer = self.dlg.getAntennaLayer()

        #If we didn't find the required layers, exit immediately.
        if surfaceLayer is None or terrainLayer is None or roadLayer is None or antennaLayer is None:
            self.dprint("Please pick which layers to use before running the calculations.")
            return

        #If no road links are selected, exit immediately
        if len(roadLayer.selectedFeatures()) <= 0:
            self.dprint("Please select at least one road link in the road layer.")
            return

        if not self.checkCrs([surfaceLayer, terrainLayer, roadLayer, antennaLayer]):
            return

        self.timeit("Starting new calculations ...", True)

        ext = iface.mapCanvas().extent()
        xmin = ext.xMinimum()
        xmax = ext.xMaximum()
        ymin = ext.yMinimum()
        ymax = ext.yMaximum()

        coords = "%f,%f,%f,%f" %(xmin, xmax, ymin, ymax)  

        surface = RasterLayer(surfaceLayer)
        terrain = RasterLayer(terrainLayer)

        #Find cell size in meters
        cell_size_meters = surface.findCellSizeInMeters()

        start_point = QgsPoint(xmin, ymax)
        end_point = QgsPoint(xmax, ymin)
        startcella = self.findcell(start_point, surface.geotransform)
        sluttcella = self.findcell(end_point, surface.geotransform)

        validAntennas = self.findValidAntennas(antennaLayer, surface.geotransform, xmin, xmax, ymin, ymax)

        #If no valid antennas remain, exit immediately.
        if len(validAntennas) <= 0:
            self.dprint("No antennae visible in canvas!")
            return   

        self.timeit("Init")

        roadpoints = self.getRoadPoints(surface, roadLayer, 5)
        
        minx = min(roadpoints, key=lambda t: t[0])[0] - 1
        miny = min(roadpoints, key=lambda t: t[1])[1] - 1
        maxx = max(roadpoints, key=lambda t: t[0])[0] + 1
        maxy = max(roadpoints, key=lambda t: t[1])[1] + 1
        rows = maxy - miny
        cols = maxx - minx
        filearray = [ [0]*cols for _ in xrange(rows) ]

        self.timeit("Roadlink setup")

        outsideOfRaster = 0
        insideRaster = 0

        for roadpoint in roadpoints:
        
            foundSignal, value, outside, inside = self.calculateSignalAtPoint(cell_size_meters, surface, terrain, validAntennas, roadpoint)

            outsideOfRaster += outside
            insideRaster += inside

            if foundSignal:
                filearray[int(roadpoint[1] - miny)][int(roadpoint[0] - minx)] = value

        # Multi threading is deactivated. The entire class needs to be restructured for this to be feasible.
        # A working mt approach is stored in asyncSignalCalculator.py, and can be used as follows (but it needs that rectructuring first!)
        #QgsMessageLog.logMessage("Threads: " + str(multiprocessing.cpu_count()), "Debug", 0)
        #calc = AsyncSignalCalculator(self, cell_size_meters, filearray, rasterHeights, validAntennas, minx, miny, roadpoints, 1)
        #calc.run()

        self.timeit("Calculations")

        resultarray = np.array(filearray)

        temp_path = os.environ['TEMP']
        tempfilename=temp_path+'temp'
        driver = gdal.GetDriverByName('GTiff')
        
        dataset = driver.Create(tempfilename,cols,rows,1,gdal.GDT_Float32)   

        txtPath = self.dlg.txtDem.toPlainText()
        if len(txtPath) > 0:
            tempfilename = txtPath

        self.array2raster(tempfilename, cols, rows, surface.geotransform, resultarray, surface.srid(), miny, minx, cell_size_meters)
        
        layer = QgsRasterLayer(tempfilename, 'resultat')
        # Add the layer to the map (comment the following line if the loading in the Layers Panel is not needed)
        iface.addRasterLayer(tempfilename, 'resultat')
        uri = str(os.path.dirname(os.path.realpath(__file__)))+"\defaultstyle.qml"
        layer.loadNamedStyle(uri)
        QgsMapLayerRegistry.instance().addMapLayer(layer,False)

        self.timeit("Done")

        if outsideOfRaster > 0:
            self.dprint("Calculations complete with warnings: " + str(outsideOfRaster) + " of the " + str(outsideOfRaster + insideRaster) + " calculation points were outside of the raster area! Maybe the projections are wrong?")
        else:
            self.dprint("Calculations complete.")

    def optimize(self):
        
        surfaceLayer = self.dlg.getSurfaceLayer()
        roadLayer = self.dlg.getRoadLayer()

        if not self.checkCrs([surfaceLayer, roadLayer]):
            return

        ext = iface.mapCanvas().extent()
        xmin = ext.xMinimum()
        xmax = ext.xMaximum()
        ymin = ext.yMinimum()
        ymax = ext.yMaximum()
        coords = "%f,%f,%f,%f" %(xmin, xmax, ymin, ymax)

        if surfaceLayer is None or roadLayer is None:
            self.dprint("Not sufficient layers for calculations")
            return

        temp_path = os.environ['TEMP']
        tempfilename=temp_path+'temp'
        driver = gdal.GetDriverByName('GTiff')
        dataset = driver.Create(tempfilename,100,100,1,gdal.GDT_Float32) 
        surface = RasterLayer(surfaceLayer)
        
        sel_features = roadlayer.selectedFeatures()
        if len(sel_features) < 1:
            self.dprint("No roadlinks selected")            
            return

        roadpoints = self.getRoadPointsForOptimize(surface, roadLayer)

        start_point = QgsPoint(xmin,ymax)
        ident = rasterfile.dataProvider().identify(QgsPoint(xmin,ymax), QgsRaster.IdentifyFormatValue)
        startcella = self.findcell(start_point,geotransform)
        end_point = QgsPoint(xmax,ymin)
        sluttcella = self.findcell(end_point,geotransform)

        roadpoints2 = self.getRoadPoints(surface, roadLayer, 10)

        minx=min(roadpoints2, key = lambda t: t[1])[0]-500
        miny=min(roadpoints2, key = lambda t: t[0])[1]-500
        maxx=max(roadpoints2, key = lambda t: t[1])[0]+500
        maxy=max(roadpoints2, key = lambda t: t[0])[1]+500
        cols2=maxy-miny
        rows2=maxx-minx
        filearray = [ [0]*cols2 for _ in xrange(rows2) ]
        #filearray = [ [0]*cols for _ in xrange(rows) ]
        f=5900*1000000 #Conv from MHz to Hz
        ant_h=10
        for roadpoint2 in roadpoints2:
            celle=roadpoint2
            signal=0
            for roadpoint in roadpoints:
                if celle != roadpoint:
                    points=self.get_cells_Bresenham(celle,roadpoint)
                    no_points=len(points)
                    length=np.sqrt((celle[0]-roadpoint[0])**2 + (celle[1]-roadpoint[1])**2)
                    std_dist=length/no_points
                    heights=[]
                    dists=[]
                    dist=0.0
                    for point in points:
                        height=data[point[1]][point[0]]
                        heights.append(height)
                        dists.append(dist)
                        dist+=std_dist
                    if len(dists)>2 and len(heights)>2:
                        #self.dprint(str(heights))
                        calc_signal=self.calculate_propagation(dists,heights,f,ant_h)
                        if calc_signal>0:
                            signal+=calc_signal
            filearray[int(celle[1]-miny)][int(celle[0]-minx)]=signal
        resultarray = np.array(filearray)
        
        resultarray *= (100.0/resultarray.max())

        writeFile=True if txtPath!=None else False
        txtPath = self.dlg.txtDem.toPlainText()
        if len(txtPath)>0:
            tempfilename=txtPath
        self.array2raster(tempfilename,cols2,rows2,geotransform,resultarray,SRID,miny,minx)
        layer = QgsRasterLayer(tempfilename, 'resultat')
        uri = str(os.path.dirname(os.path.realpath(__file__)))+"\default_optimize.qml"
        layer.loadNamedStyle(uri)
        # Add the layer to the map (comment the following line if the loading in the Layers Panel is not needed)
        iface.addRasterLayer(tempfilename, 'resultat')
        QgsMapLayerRegistry.instance().addMapLayer(layer,False)
        #layer.loadNamedStyle(uri)
        #iface.legendInterface().refreshLayerSymbology(layer)
        #self.dprint(uri)
        #iface.messageBar().clearWidgets() 
        self.dprint("Calculations complete")

    
    def run(self):
        """Run method that performs all the real work"""
        #For each point in raster: Calculate best coverage
        #Use Bresenham between antennae and raster cells.
        # show the dialog
        self.dlg.listLayers()
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:

            if self.dlg.rb_plotHeight.isChecked():
                self.printHeightProfile()
                
            elif self.dlg.rb_calcSignal.isChecked():
                self.calculateSignal()

            elif self.dlg.rb_optimize.isChecked():
                self.optimize()

            else:
                self.dprint("Please choose an option.")


    def rasterizer(self, shapePath, rasterPath, attribute, cols,rows,geotransform,SRID):
        '''Rasterize a shapefile using its attribute value
            @param shapePath    Input shapefile
            @param rasterPath   Output rasterfile
            @param attribute    Attribute fieldname (string)
            @gridModelPath      grid used to as reference'''
        # Import data, geotransform and projection from the model grid
        #data, geotransform, prj_wkt = rasterReader(gridModelPath)
        RasterYSize, RasterXSize = rows,cols

        # Import data from the vector layer
        driver = ogr.GetDriverByName('ESRI Shapefile')
        vector_source = driver.Open(shapePath,0)
        source_layer = vector_source.GetLayer(0)

        target_ds = gdal.GetDriverByName( 'MEM' ).Create( "", RasterXSize, RasterYSize, 1, gdal.GDT_Int32)
        target_ds.SetGeoTransform( geotransform )
        outRasterSRS = osr.SpatialReference()
        outRasterSRS.ImportFromEPSG(SRID)
        target_ds.SetProjection( outRasterSRS.ExportToWkt() )
        # Rasterise!
        err = gdal.RasterizeLayer(target_ds, [1], source_layer,
            options=["ATTRIBUTE=%s" % attribute ])
        if err != 0:
            raise Exception("error rasterizing layer: %s" % err)
        data = target_ds.ReadAsArray()
        # Write your data on the disk
        #rasterWriter(data, rasterPath, geotransform, prj_wkt, gdal.GDT_Int32)
        return data

    def array2raster(self,filename,cols,rows,geotransform,array,SRID,miny,minx,cell_size_meters):

        originX = geotransform[0]+cell_size_meters*minx
        originY = geotransform[3]-cell_size_meters*miny
        pixelWidth = geotransform[1]
        pixelHeight = geotransform[5]
        #driver = gdal.GetDriverByName('USGSDEM')
        driver = gdal.GetDriverByName('GTiff')
        outRaster = driver.Create(filename, cols, rows, 1, gdal.GDT_Float32)
        outRaster.SetGeoTransform((originX, pixelWidth, geotransform[2], originY, geotransform[4], pixelHeight))
        outband = outRaster.GetRasterBand(1)
        outband.WriteArray(array)
        outRasterSRS = osr.SpatialReference()
        outRasterSRS.ImportFromEPSG(SRID)
        outRaster.SetProjection(outRasterSRS.ExportToWkt())
        outband.FlushCache()

    def findcell(self, point, geotransform):
        originX = geotransform[0]
        originY = geotransform[3]
        pixelWidth = geotransform[1]
        pixelHeight = geotransform[5]
        startxOffset = int((point[0] - originX)/pixelWidth)
        startyOffset = int((point[1] - originY)/pixelHeight)
        start = (startxOffset, startyOffset)
        return start
        
    def writeToFile(self,filestring,txtPath,writeFile):
        if writeFile:
            fil=open(txtPath,'w')
            for element in filestring:
                fil.write(element)
            fil.close()        

    def combine_and_sort(self,xdist,xheight,ydist,yheight,filestring):
        comb_height=xheight+yheight
        #comb_height_skog=xheight_skog+yheight_skog
        comb_dist=xdist+ydist
        dist,height = (list(t) for t in zip(*sorted(zip( comb_dist,comb_height))))
        
        filestring.append("Heights: \n")
        filestring.append(str(height)+"\n")
        filestring.append("Distances: \n")
        filestring.append(str(dist)+"\n")
        #filestring.append("Tree heights: \n")
        #filestring.append(str(height_skog)+"\n")
        
        return dist,height#,height_skog
        
    def get_heights_along_x(self,ants,geotransform,data,cell_size_meters):
        originX = geotransform[0]
        originY = geotransform[3]
        pixelWidth = geotransform[1]
        pixelHeight = geotransform[5]
        #startxOffset = int((ants[0][0] - originX)/pixelWidth)
        #startyOffset = int((ants[0][1] - originY)/pixelHeight)
        endxOffset=ants[0][0]
        endyOffset=ants[0][1]
        startxOffset = int((ants[1][0] - originX)/pixelWidth)
        startyOffset = int((ants[1][1] - originY)/pixelHeight)
        start=(startxOffset,startyOffset)
        end=(endxOffset,endyOffset)
        points=[]
        #startx=float((ants[0][0] - originX)/float(pixelWidth))-startxOffset
        #starty=float((ants[0][1] - originY)/float(pixelHeight))-startyOffset
        endx=0.5
        endy=0.5
        startx=float((ants[1][0] - originX)/float(pixelWidth))-startxOffset
        starty=float((ants[1][1] - originY)/float(pixelHeight))-startyOffset
        startcoord=(startx+startxOffset,starty+startyOffset)
        endcoord=(endx+endxOffset,endy+endyOffset)
        points.append(startcoord)
        x1, y1 = startcoord
        x2, y2 = endcoord
        dx = x2 - x1
        dy = y2 - y1
        heights=[]
        distances=[]
        rise=dy/float(dx)
        positive=True if x2>x1 else False
        if startx>0.5:
            if starty>0.5:
                startheight=self.bilinear(startxOffset,startxOffset+1,startyOffset,startyOffset+1,startx+startxOffset,starty+startyOffset,data)
                #startheight_skog=self.bilinear(startxOffset,startxOffset+1,startyOffset,startyOffset+1,startx+startxOffset,starty+startyOffset,data_skog)
            else:
                startheight=self.bilinear(startxOffset,startxOffset+1,startyOffset-1,startyOffset,startx+startxOffset,starty+startyOffset,data)
                #startheight_skog=self.bilinear(startxOffset,startxOffset+1,startyOffset-1,startyOffset,startx+startxOffset,starty+startyOffset,data_skog)
        else:
            if starty>0.5:
                startheight=self.bilinear(startxOffset-1,startxOffset,startyOffset,startyOffset+1,startx+startxOffset,starty+startyOffset,data)
                #startheight_skog=self.bilinear(startxOffset-1,startxOffset,startyOffset,startyOffset+1,startx+startxOffset,starty+startyOffset,data_skog)
            else:
                startheight=self.bilinear(startxOffset-1,startxOffset,startyOffset-1,startyOffset,startx+startxOffset,starty+startyOffset,data)
                #startheight_skog=self.bilinear(startxOffset-1,startxOffset,startyOffset-1,startyOffset,startx+startxOffset,starty+startyOffset,data_skog)
        heights.append(startheight)
        #heights_skog.append(startheight_skog)
        if startx>0.5:
            if starty>0.5:
                endheight=self.bilinear(endxOffset,endxOffset+1,endyOffset,endyOffset+1,endx+endxOffset,endy+endyOffset,data)
                #endheight_skog=self.bilinear(endxOffset,endxOffset+1,endyOffset,endyOffset+1,endx+endxOffset,endy+endyOffset,data_skog)
            else:
                endheight=self.bilinear(endxOffset,endxOffset+1,endyOffset-1,endyOffset,endx+endxOffset,endy+endyOffset,data)
                #endheight_skog=self.bilinear(endxOffset,endxOffset+1,endyOffset-1,endyOffset,endx+endxOffset,endy+endyOffset,data_skog)
        else:
            if starty>0.5:
                endheight=self.bilinear(endxOffset-1,endxOffset,endyOffset,endyOffset+1,endx+endxOffset,endy+endyOffset,data)
                #endheight_skog=self.bilinear(endxOffset-1,endxOffset,endyOffset,endyOffset+1,endx+endxOffset,endy+endyOffset,data_skog)
            else:
                endheight=self.bilinear(endxOffset-1,endxOffset,endyOffset-1,endyOffset,endx+endxOffset,endy+endyOffset,data)
                #endheight_skog=self.bilinear(endxOffset-1,endxOffset,endyOffset-1,endyOffset,endx+endxOffset,endy+endyOffset,data_skog) 
        dist=0.0
        distances.append(dist)
        if positive:
            lasty=starty+startyOffset-startx*rise
            for x in range(startxOffset+1,endxOffset+1):
                coord=(x,lasty+rise)
                distances.append(cell_size_meters*np.sqrt(abs(coord[0]-startcoord[0])**2+abs(coord[1]-startcoord[1])**2))
                lasty+=rise
                points.append(coord)
                yfloor=int(np.floor(coord[1]))
                if coord[1]-yfloor>0.5:
                    height=self.bilinear(x-1,x,yfloor-1,yfloor,coord[0],coord[1],data)
                    #height_skog=self.bilinear(x-1,x,yfloor-1,yfloor,coord[0],coord[1],data_skog)
                else:
                    height=self.bilinear(x-1,x,yfloor,yfloor+1,coord[0],coord[1],data)
                    #height_skog=self.bilinear(x-1,x,yfloor,yfloor+1,coord[0],coord[1],data_skog)
                heights.append(height)
                #heights_skog.append(height_skog)
            points.append(endcoord)
            heights.append(endheight)
            #heights_skog.append(endheight_skog)
            distances.append(cell_size_meters*np.sqrt(abs(endcoord[0]-startcoord[0])**2+abs(endcoord[1]-startcoord[1])**2)) 
        else:
            rise=rise*(-1)
            lasty=starty+startyOffset-(1-startx)*rise
            for x in range(startxOffset,endxOffset,-1):
                coord=(x,lasty+rise)
                distances.append(cell_size_meters*np.sqrt(abs(coord[0]-startcoord[0])**2+abs(coord[1]-startcoord[1])**2))
                lasty+=rise
                points.append(coord)
                yfloor=int(np.floor(coord[1]))
                if coord[1]-yfloor>0.5:
                    height=self.bilinear(x-1,x,yfloor-1,yfloor,coord[0],coord[1],data)
                    #height_skog=self.bilinear(x-1,x,yfloor-1,yfloor,coord[0],coord[1],data_skog)
                else:
                    height=self.bilinear(x-1,x,yfloor,yfloor+1,coord[0],coord[1],data)
                    #height_skog=self.bilinear(x-1,x,yfloor,yfloor+1,coord[0],coord[1],data_skog)
                heights.append(height)
                #heights_skog.append(height_skog)
            points.append(endcoord)
            heights.append(endheight)
            #heights_skog.append(endheight_skog)
            distances.append(cell_size_meters*np.sqrt(abs(endcoord[0]-startcoord[0])**2+abs(endcoord[1]-startcoord[1])**2))
        '''
        fil=open(txtPath,'w')
        fil.write("Points: \n")
        fil.write(str(points)+"\n")
        fil.write("Heights: \n")
        fil.write(str(heights)+"\n")
        fil.write("Distances: \n")
        fil.write(str(distances)+"\n")
        fil.close()
        '''
        return distances,heights#,heights_skog
        

    def get_heights_along_y(self,ants,geotransform,data,cell_size_meters):
        originX = geotransform[0]
        originY = geotransform[3]
        pixelWidth = geotransform[1]
        pixelHeight = geotransform[5]
        #startxOffset = int((ants[0][0] - originX)/pixelWidth)
        #startyOffset = int((ants[0][1] - originY)/pixelHeight)
        endxOffset=ants[0][0]
        endyOffset=ants[0][1]
        startxOffset = int((ants[1][0] - originX)/pixelWidth)
        startyOffset = int((ants[1][1] - originY)/pixelHeight)
        start=(startxOffset,startyOffset)
        end=(endxOffset,endyOffset)
        points=[]
        #startx=float((ants[0][0] - originX)/float(pixelWidth))-startxOffset
        #starty=float((ants[0][1] - originY)/float(pixelHeight))-startyOffset
        endx=0.5
        endy=0.5
        startx=float((ants[1][0] - originX)/float(pixelWidth))-startxOffset
        starty=float((ants[1][1] - originY)/float(pixelHeight))-startyOffset
        startcoord=(startx+startxOffset,starty+startyOffset)
        endcoord=(endx+endxOffset,endy+endyOffset)
        #points.append(startcoord)
        x1, y1 = startcoord
        x2, y2 = endcoord
        dx = x2 - x1
        dy = y2 - y1
        heights=[]
        distances=[]
        #heights_skog=[]
        rise=dx/float(dy)
        positive=True if y2>y1 else False

        if positive:
            lastx=startx+startxOffset-starty*rise #starty+startyOffset-startx*rise
            for y in range(startyOffset+1,endyOffset+1):
                coord=(lastx+rise,y)#(x,lasty+rise)
                distances.append(cell_size_meters*np.sqrt(abs(coord[0]-startcoord[0])**2+abs(coord[1]-startcoord[1])**2))
                lastx+=rise
                points.append(coord)
                xfloor=int(np.floor(coord[0]))
                if coord[0]-xfloor>0.5:
                    height=self.bilinear(xfloor,xfloor+1,y-1,y,coord[0],coord[1],data)
                    #height_skog=self.bilinear(xfloor,xfloor+1,y-1,y,coord[0],coord[1],data_skog)
                else:
                    height=self.bilinear(xfloor-1,xfloor,y-1,y,coord[0],coord[1],data)
                    #height_skog=self.bilinear(xfloor-1,xfloor,y-1,y,coord[0],coord[1],data_skog)
                heights.append(height)
                #heights_skog.append(height_skog)
            #points.append(endcoord)
            #heights.append(endheight)
            #distances.append(10*np.sqrt(abs(endcoord[0]-startcoord[0])**2+abs(endcoord[1]-startcoord[1])**2)) 
        else:
            rise=rise*(-1)
            lastx=startx+startxOffset-(1-starty)*rise
            for y in range(startyOffset,endyOffset,-1):
                coord=(lastx+rise,y)
                distances.append(cell_size_meters*np.sqrt(abs(coord[0]-startcoord[0])**2+abs(coord[1]-startcoord[1])**2))
                lastx+=rise
                points.append(coord)
                xfloor=int(np.floor(coord[0]))
                if coord[0]-xfloor>0.5:
                    height=self.bilinear(xfloor,xfloor+1,y-1,y,coord[0],coord[1],data)
                    #height_skog=self.bilinear(xfloor,xfloor+1,y-1,y,coord[0],coord[1],data_skog)
                else:
                    height=self.bilinear(xfloor-1,xfloor,y-1,y,coord[0],coord[1],data)
                    #height_skog=self.bilinear(xfloor-1,xfloor,y-1,y,coord[0],coord[1],data_skog)
                heights.append(height)
                #heights_skog.append(height_skog)
            #points.append(endcoord)
            #heights.append(endheight)
            #distances.append(10*np.sqrt(abs(endcoord[0]-startcoord[0])**2+abs(endcoord[1]-startcoord[1])**2))
        '''
        fil=open(txtPath,'w')
        fil.write("Points: \n")
        fil.write(str(points)+"\n")
        fil.write("Heights: \n")
        fil.write(str(heights)+"\n")
        fil.write("Distances: \n")
        fil.write(str(distances)+"\n")
        fil.close()
        '''
        return distances,heights#,heights_skog

    def get_cells_Bresenham(self,startcelle,sluttcelle):
        """Yield integer coordinates on the line from (x0, y0) to (x1, y1).
        Input coordinates should be integers.
        The result will contain both the start and the end point.
        """

        #Implementation fetched from: https://pypi.python.org/pypi/bresenham

        # Setup initial conditions
        x0, y0 = startcelle
        x1, y1 = sluttcelle
        
        dx = x1 - x0
        dy = y1 - y0

        xsign = 1 if dx > 0 else -1
        ysign = 1 if dy > 0 else -1

        dx = abs(dx)
        dy = abs(dy)

        if dx > dy:
            xx, xy, yx, yy = xsign, 0, 0, ysign
        else:
            dx, dy = dy, dx
            xx, xy, yx, yy = 0, ysign, xsign, 0

        D = 2*dy - dx
        y = 0

        points = []
        for x in range(dx + 1):
            points.append((x0 + x*xx + y*yx, y0 + x*xy + y*yy))
            if D > 0:
                y += 1
                D -= dx
            D += dy
      
        return points
