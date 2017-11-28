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
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QDateEdit, QColor, QFileDialog, QButtonGroup
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from Hybriddekning_dialog import HybriddekningDialog
import os.path
from osgeo import osr, gdal, ogr
from qgis.gui import QgsMessageBar
from qgis.utils import iface
import numpy as np
import scipy.ndimage as ndimage
from qgis.core import *
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

    def calculate_propagation(self):
        """Runs the propagation model for the selected layers """
        pass

    def bilinear(self, x1,x2,y1,y2,x,y,data):
        p=data[y1][x1]*(x2-x)*(y2-y)+data[y1][x2]*(x-x1)*(y2-y)+data[y2][x1]*(x2-x)*(y-y1)+data[y2][x2]*(x-x1)*(y-y1)
        return p
    
    def get_line(self,data,ants,geotransform,txtPath):
        originX = geotransform[0]
        originY = geotransform[3]
        pixelWidth = geotransform[1]
        pixelHeight = geotransform[5]
        startxOffset = int((ants[0][0] - originX)/pixelWidth)
        startyOffset = int((ants[0][1] - originY)/pixelHeight)
        endxOffset = int((ants[1][0] - originX)/pixelWidth)
        endyOffset = int((ants[1][1] - originY)/pixelHeight)
        start=(startxOffset,startyOffset)
        end=(endxOffset,endyOffset)
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
     
        # Determine how steep the line is
        is_steep = abs(dy) > abs(dx)
     
        # Rotate line
        if is_steep:
            x1, y1 = y1, x1
            x2, y2 = y2, x2
     
        # Swap start and end points if necessary and store swap state
        swapped = False
        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1
            swapped = True
     
        # Recalculate differentials
        dx = x2 - x1
        dy = y2 - y1
     
        # Calculate error
        error = int(dx / 2.0)
        ystep = 1 if y1 < y2 else -1
     
        # Iterate over bounding box generating points between start and end
        y = y1
        y_cord=y1
        x_cord=x1
        startx=float((ants[0][0] - originX)/float(pixelWidth))-startxOffset
        starty=float((ants[0][1] - originY)/float(pixelHeight))-startyOffset
        startcoord=(starty+startyOffset,startx+startxOffset) if is_steep else (startx+startxOffset,starty+startyOffset)
        if ystep>0:
            ydiff = 1.0-starty
        else:
            ydiff=starty
        xdiff = 1.0-startx
        points = []
        distances=[]
        points.append(startcoord)
        heights=[]
        steepness=dy/float(dx)
        dist=0
        #iface.messageBar().pushMessage("Output", str(data[10][0]), level=QgsMessageBar.INFO)
        #dist+=np.sqrt(xdiff*xdiff+ydiff*ydiff)
        #bilinear(self, x1,x2,y1,y2,x,y,q11,q12,q21,q22):
        #self.dprint("{0} {1} {2} {3}".format(startxOffset,startyOffset,xdiff,ydiff))
        #self.dprint(str(data[startyOffset][startxOffset]))
        if startx>0.5:
            if starty>0.5:
                height=self.bilinear(startxOffset,startxOffset+1,startyOffset,startyOffset+1,startx+startxOffset,starty+startyOffset,data)
            else:
                height=self.bilinear(startxOffset,startxOffset+1,startyOffset-1,startyOffset,startx+startxOffset,starty+startyOffset,data)
        else:
            if starty>0.5:
                height=self.bilinear(startxOffset-1,startxOffset,startyOffset,startyOffset+1,startx+startxOffset,starty+startyOffset,data)
            else:
                height=self.bilinear(startxOffset-1,startxOffset,startyOffset-1,startyOffset,startx+startxOffset,starty+startyOffset,data)
        heights.append(height)
        distances.append(dist)
        celldist=np.sqrt(100+steepness*steepness*100)
        for x in range(x1, x2 + 1):
            if ystep>0:
                ydiff+=steepness
            else:
                ydiff-=steepness
            if ydiff<1.0 and ydiff>0.0:#dx equals 1
                dist+=celldist
                distances.append(dist)
                y_cord = y+ydiff if ystep>0 else y-ydiff
                x_cord=x+1
                coord2 = (y_cord,x_cord) if is_steep else (x_cord,y_cord)
                points.append(coord2)
                if is_steep:
                    if abs(ydiff)<0.5:
                        height=self.bilinear(y-1,y,x,x+1,y+ydiff,x+1,data)
                        #height=data[y+1][x+1]-(ydiff)*(data[y][x+1]-data[y+1][x+1])
                    else:
                        height=self.bilinear(y,y+1,x,x+1,y+ydiff,x+1,data)
                        #height=data[y+1][x+1]-(ydiff)*(data[y][x+1]-data[y+1][x+1])
                    height=data[y][x+1]+(ydiff)*(data[y+1][x+1]-data[y][x+1])
                else:
                    if abs(ydiff)<0.5:
                        height=self.bilinear(x,x+1,y-1,y,x+1,y+ydiff,data)
                        #height=data[y+1][x+1]-(ydiff)*(data[y][x+1]-data[y+1][x+1])
                    else:
                        height=self.bilinear(x,x+1,y,y+1,x+1,y+ydiff,data)
                        #height=data[y+1][x+1]-(ydiff)*(data[y][x+1]-data[y+1][x+1])   
                heights.append(height)
                #height=ndimage.map_coordinates(data2.astype(float), [[0], [coord2[1]], [coord2[0]]])
                #heights.append(height)
            else: #y increases before dx=1, so we need two points
                #First point: crossing the floor
                if ydiff<0.0:
                    ydiff += 1
                else:
                    ydiff -= 1
                x_dist=np.sqrt(100*(ydiff/steepness)*(ydiff/steepness)+ydiff*ydiff*100)
                dist+=x_dist
                distances.append(dist)
                x_diff=(ydiff/steepness)
                y_cord = y+ydiff if ystep>0 else y-ydiff
                if is_steep:
                    x_cord = x+(x_diff)
                else:
                    x_cord = x -(x_diff)#???
                coord2 = (y_cord,x_cord) if is_steep else (x_cord,y_cord)
                points.append(coord2)
                #if is_steep:
                 #   height=data[y+1][x+1]+(ydiff/steepness)*(data[y+1][x+2]-data[y+1][x+1])
                #else:
                 #   height=data[y+1][x+1]-(ydiff/steepness)*(data[y+1][x+2]-data[y+1][x+1])
                if is_steep:
                    if abs(xdiff)<0.5:
                        height=self.bilinear(y-1,y,x-1,x,y,x+xdiff,data)
                        #height=data[y+1][x+1]-(ydiff)*(data[y][x+1]-data[y+1][x+1])
                    else:
                        height=self.bilinear(y-1,y,x,x+1,y,x+xdiff,data)
                        #height=data[y+1][x+1]-(ydiff)*(data[y][x+1]-data[y+1][x+1])
                    #height=data[y][x+1]+(ydiff)*(data[y+1][x+1]-data[y][x+1])
                else:
                    if abs(xdiff)<0.5:
                        height=self.bilinear(x-1,x,y-1,y,x+xdiff,y,data)
                        #height=data[y+1][x+1]-(ydiff)*(data[y][x+1]-data[y+1][x+1])
                    else:
                        height=self.bilinear(x,x+1,y-1,y,x+xdiff,y,data)
                heights.append(height)
                #height=ndimage.map_coordinates(data2.astype(float), [[0], [coord2[1]], [coord2[0]]])
                #heights.append(height)
                #Second point: Reaching dx=1
                dist+=celldist-x_dist #Need to subtract the dist over the floor
                distances.append(dist)
                y_cord = y+ydiff if ystep>0 else y-ydiff
                x_cord=x+1
                coord2 = (y_cord,x_cord) if is_steep else (x_cord,y_cord)
                points.append(coord2)
                if is_steep:
                    if abs(ydiff)<0.5:
                        height=self.bilinear(y-1,y,x,x+1,y+ydiff,x+1,data)
                        #height=data[y+1][x+1]-(ydiff)*(data[y][x+1]-data[y+1][x+1])
                    else:
                        height=self.bilinear(y,y+1,x,x+1,y+ydiff,x+1,data)
                        #height=data[y+1][x+1]-(ydiff)*(data[y][x+1]-data[y+1][x+1])
                    height=data[y][x+1]+(ydiff)*(data[y+1][x+1]-data[y][x+1])
                else:
                    if abs(ydiff)<0.5:
                        height=self.bilinear(x,x+1,y-1,y,x+1,y+ydiff,data)
                        #height=data[y+1][x+1]-(ydiff)*(data[y][x+1]-data[y+1][x+1])
                    else:
                        height=self.bilinear(x,x+1,y,y+1,x+1,y+ydiff,data)
                        #height=data[y+1][x+1]-(ydiff)*(data[y][x+1]-data[y+1][x+1])   
                heights.append(height)
                #height=ndimage.map_coordinates(data2.astype(float), [[0], [coord2[1]], [coord2[0]]])
                #heights.append(height)

                
                
               
            #coord = (y, x) if is_steep else (x, y)
            
            error -= abs(dy)
            if error < 0:
                y += ystep
                error += dx
            
            
     
        # Reverse the list if the coordinates were swapped
        if swapped:
            points.reverse()

        
        #data2 = np.arange(9).reshape(1,3,3)


        #test_value= ndimage.map_coordinates(data2.astype(float), [[0], [1.5], [1.5]])
        #fil=open("C:/Users/ohje/heights.txt",'w')
        fil=open(txtPath,'w')
        #for point in heights[:2]:
            #value = data[point[1], point[0]]
            #height=ndimage.map_coordinates(data2.astype(float), [[0], [point[1]], [point[0]]])
            #heights.append(height)

        fil.write("Heights: \n")            
        fil.write(str(heights)+"\n")
        fil.write("Distances: \n")
        fil.write(str(distances)+"\n")
        fil.write("Points: \n")
        fil.write(str(points)+"\n") 
        fil.close()

        #iface.messageBar().pushMessage("Output", str(test_value), level=QgsMessageBar.INFO)
        #iface.messageBar().pushMessage("Output", str(points), level=QgsMessageBar.INFO)


    def dprint(self,msg):
        QMessageBox.information(self.iface.mainWindow(),"Debug",msg)
    def open_txt_file(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select .txt-file to write to", "", "*.txt")
        self.dlg.txtDem.setText(filename)        
    def run(self):
        """Run method that performs all the real work"""
        #layers=self.iface.legendInterface().layers()
        #layer_list=[]
        #for layer in layers:
            #layer_list.append(layer.name())
        #self.dlg.terrain_box.addItems(layer_list)
        #self.dlg.antenna_box.addItems(layer_list)
        #self.dlg.out_box.addItems(layer_list)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            txtPath = self.dlg.txtDem.toPlainText()
            #self.dprint(txtPath)
            foundraster=False
            foundvector=False
            layernim = iface.activeLayer().name()
            checkednames=[]
            checkedlayers=iface.mapCanvas().layers()
            for checklayer in checkedlayers:
                checkednames.append(checklayer.name())
            
            for lyr in QgsMapLayerRegistry.instance().mapLayers().values():
                if type(lyr) is QgsRasterLayer and lyr.name() in checkednames:
                    self.dprint("Using layer: {0} for terrain".format(lyr.name()))
                    rasterfilename=lyr.source()
                    foundraster=True
                if type(lyr) is QgsVectorLayer and lyr.name() in checkednames:
                    self.dprint("Using layer: {0} for antennas".format(lyr.name()))
                    antennaLayer=lyr
                    foundvector=True
            if foundvector and foundraster:

                ants=[]
                iter = antennaLayer.getFeatures()
                for feature in iter:
                    ants.append(feature.geometry().asPoint())
                raster = gdal.Open(rasterfilename)
                cols = raster.RasterXSize
                rows = raster.RasterYSize
                bands = raster.RasterCount
                band = raster.GetRasterBand(1)
                geotransform = raster.GetGeoTransform()


                data = band.ReadAsArray(0, 0, cols, rows)
                #self.get_line(data,ants,geotransform,txtPath)
                self.get_cells_Bresenham(ants,geotransform,txtPath)
                self.dprint("Calculations complete")
                
            else:
                self.dprint("Not sufficient layers for calculations")
                        #iface.messageBar().pushMessage("Output", str(originX), level=QgsMessageBar.INFO)
            

            #teststring=[startxOffset,startyOffset,endxOffset,endyOffset]
            #linje=get_line((startxOffset,startyOffset),(endxOffset,endyOffset))
            #data2=data.reshape(1,cols,rows)

            
            #rasterlayer=self.dlg.terrain_box.currentText()
            #antennelayer=self.dlg.antenna_box.currentText()
            #selectedLayerIndex = self.dlg.terrain_box.currentIndex()
            #selectedLayer = layers[selectedLayerIndex]
            #fields = selectedLayer.pendingFields()
            #fieldnames = [field.name() for field in fields]
            # iface.messageBar().pushMessage("Output", rasterlayer, level=QgsMessageBar.INFO)

            #selectedLayerIndex2 = self.dlg.antenna_box.currentIndex()
            #selectedLayer2 = layers[selectedLayerIndex2]
            #feature = selectedLayer2.getFeatures().next()
            #startpoint = feature.geometry().asPoint()
            #feature2=selectedLayer2.getFeatures().next()
            #endpoint=feature2.geometry().asPoint()
            #ident = selectedLayer.dataProvider().identify(startpoint,QgsRaster.IdentifyFormatValue)
            #if ident.isValid():
                #iface.messageBar().pushMessage("Output", str(ident.results().get(1)), level=QgsMessageBar.INFO)

            # iface.messageBar().pushMessage("Output", polygon, level=QgsMessageBar.INFO)
            

            '''
            indices, weight = route_through_array(costSurfaceArray, (startIndexY,startIndexX), (stopIndexY,stopIndexX),geometric=True,fully_connected=True)
            indices = np.array(indices).T
            path = np.zeros_like(costSurfaceArray)
            path[indices[0], indices[1]] = 1
            '''
            '''
            gdal_raster=gdal.Open(RasterPath)
            gt=gdal_raster.GetGeoTransform()#daje podatke o rasteru (metadata)
            projection= gdal_raster.GetProjection()
            global pix; pix=gt[1] # there's a bug in Python: globals cannot be avoided by a nested function (??)
            global raster_x_min; raster_x_min = gt[0]
            global raster_y_max; raster_y_max = gt[3] # it's top left y, so maximum!

            raster_y_size = gdal_raster.RasterYSize
            raster_x_size = gdal_raster.RasterXSize

            raster_y_min = raster_y_max - raster_y_size * pix
            raster_x_max = raster_x_min + raster_x_size * pix
            '''


    def get_cells_Bresenham(self,ants,geotransform,txtPath):
        originX = geotransform[0]
        originY = geotransform[3]
        pixelWidth = geotransform[1]
        pixelHeight = geotransform[5]
        startxOffset = int((ants[0][0] - originX)/pixelWidth)
        startyOffset = int((ants[0][1] - originY)/pixelHeight)
        endxOffset = int((ants[1][0] - originX)/pixelWidth)
        endyOffset = int((ants[1][1] - originY)/pixelHeight)
        start=(startxOffset,startyOffset)
        end=(endxOffset,endyOffset)
        # Setup initial conditions
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1


     
        # Determine how steep the line is
        is_steep = abs(dy) > abs(dx)
     
        # Rotate line
        if is_steep:
            x1, y1 = y1, x1
            x2, y2 = y2, x2
     
        # Swap start and end points if necessary and store swap state
        swapped = False
        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1
            swapped = True
     
        # Recalculate differentials
        dx = x2 - x1
        dy = y2 - y1
     
        # Calculate error
        error = int(dx / 2.0)
        ystep = 1 if y1 < y2 else -1
     
        # Iterate over bounding box generating points between start and end
        y = y1
        points = []
        for x in range(x1, x2 + 1):
            coord = (y, x) if is_steep else (x, y)
            points.append(coord)
            error -= abs(dy)
            if error < 0:
                y += ystep
                error += dx
     
        # Reverse the list if the coordinates were swapped
        if swapped:
            points.reverse()
        fil=open(txtPath,'w')
        fil.write("Points: \n")
        fil.write(str(points)+"\n") 
        fil.close()
        
    def get_heights_quadrant(self,cells, startpoint,endpoint,quadrant,dx,dy,geotransform):
        #cells=[(x1,y1),(x2,y2),...]
        originX = geotransform[0]
        originY = geotransform[3]
        pixelWidth = geotransform[1]
        pixelHeight = geotransform[5]
        startxOffset = cells[0][0]
        startyOffset = cells[0][1]
        no_cls=len(cells)
        endxOffset = cells[no_cls][0]
        endyOffset = cells[no_cls][1]
        start=(startxOffset,startyOffset)
        end=(endxOffset,endyOffset)
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        rise=int(100.0*dy/float(dx))
        inv_rise=int(100.0*dx/float(dy))
        if quadrant==1:
            #Treat starpoint first
            dx_new=int(100.0*float((startpoint[0][0] - originX)/float(pixelWidth)))
            dy_new=int(100.0*float((startpoint[0][1] - originY)/float(pixelHeight)))
            startx=float((startpoint[0][0] - originX)/float(pixelWidth))-startxOffset
            starty=float((startpoint[0][1] - originY)/float(pixelHeight))-startyOffset
            #startcoord=(starty+startyOffset,startx+startxOffset)
            #if ystep>0:
             #   ydiff = 1.0-starty
            #else:
             #   ydiff=starty
            #xdiff = 1.0-startx
            points = []
            distances=[]
            points.append(startcoord)
            heights=[]
            #steepness=dy/float(dx)
            dist=0
            #Get first height
            #Get wall , 1 or 2
            #prev_wall=1
            #Get percentage of x or y
            #prev_perc=80
            #Get height of first intercept
            '''
            if startx>0.5:
                if starty>0.5:
                    height=self.bilinear(startxOffset,startxOffset+1,startyOffset,startyOffset+1,startx+startxOffset,starty+startyOffset,data)
                else:
                    height=self.bilinear(startxOffset,startxOffset+1,startyOffset-1,startyOffset,startx+startxOffset,starty+startyOffset,data)
            else:
                if starty>0.5:
                    height=self.bilinear(startxOffset-1,startxOffset,startyOffset,startyOffset+1,startx+startxOffset,starty+startyOffset,data)
                else:
                    height=self.bilinear(startxOffset-1,startxOffset,startyOffset-1,startyOffset,startx+startxOffset,starty+startyOffset,data)
            heights.append(height)
            distances.append(dist)
            celldist_x=np.sqrt(100*100+rise*rise)
            celldist_y=np.sqrt(100*100+inv_rise*inv_rise)
            

            for cell in cells:
                #Skip first cell, this where the startpoint is
                #If prev_perc was 100: The point is in the intercept, we dont need another point
                if prev_wall==1:#Move along y-axis
                    this_wall=4
                    
                    #Previous perc was along the x-axis. The breach was x units from 0, whixh means there are
                    #100-x units left. For dx units, the rise is dx*dy/dx=dy. This means the curr_perc equals 100 minus dy.
                    #The coordinates are x,y+(100-dy).

                    #Find height
                    
                    #How will this be if quadrant equals 2? Positive x and positive y. Mirror method. The difference is that y increases instead of decrease.
                    #How will this be if quadrant equals 3? Neagtive x and positive y. Flip method. The difference is that y increase and x decrease.
                    #How will this be if quadrant equals 4? Negativ x and negative y. Mirror method. The differenc eis that x decreases.
                    
                    #If curr_perc is larger than dy, point number two is also on the y-axis
                    #The coordinates are x+1,y+(curr_perc-dy)
                    #Find height

                    #If curr_perc is lower than dy, point number two is on the x-axis. 
                    #The breach is x units higher than x. To find dx, we use that new_dy=(_olddy-curr_perc), and x=x+dy*dx/dy, and the y-coord is y.
                    #Find height
                else:
                    this_wall=3 #Move along x-axis
                    #Previous point was along the y-axis. The breach was y units from 0, which means there are 100-y units left.
                    #For dy units, the travel along x is dy*dx/dy=dx. Thismeans the curr_perc equals 100 minus dx.
                    #The coordinates are x+(100-dx),y+1

                    #Find height

                    #If curr_perc is larger than dx, point number two is also on the x axis
                    #The coordinates are x+(curr_perc-dx),y
                    #Find height

                    #If curr_perc is lower than dx, pointnumber two is on the y-axis.
                    #The breach is y units higher than y. To find dy, we use that new_dx=(old_dx-curr_perc), and x=x+1, y=y+dx*dy/dx
                    #Find height
            
                    
                '''
                 
                    
                
    #def get_heights_horizontal(self,cells,direction):

    
    #def get_heights_horizontal(self,cells,direction):
        
