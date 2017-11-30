# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HybriddekningDialog
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

import os

from PyQt4 import QtGui, uic
from qgis.utils import iface
from qgis.core import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Hybriddekning_dialog_base.ui'))


class HybriddekningDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(HybriddekningDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

    def listLayers(self):

        self.rasterLayers = []
        self.roadLayers = []
        self.antennaLayers = []

        #Enumerate all layers and pick the layers to show the user
        for layer in iface.mapCanvas().layers():

            if type(layer) is QgsRasterLayer:
                self.rasterLayers.append(layer)
            if type(layer) is QgsVectorLayer and layer.geometryType() == 1: #layer.geometryType() #0=points, 1=line, 2=polygon
                self.roadLayers.append(layer)
            if type(layer) is QgsVectorLayer and layer.geometryType() == 0:
                self.antennaLayers.append(layer)

        def setItems(com, items):
            com.clear()
            for item in items:
                com.addItem(item.name())

        #Update the comboboxes
        setItems(self.comSurface, self.rasterLayers)
        setItems(self.comTerrain, self.rasterLayers)
        setItems(self.comRoad, self.roadLayers)
        setItems(self.comAntenna, self.antennaLayers)

    def __getLayer(self, com, items):

        idx = com.currentIndex()

        if idx < 0 or idx >= len(items):
            return None

        return items[idx]

    def getSurfaceLayer(self):
        return self.__getLayer(self.comSurface, self.rasterLayers)

    def getTerrainLayer(self):
        return self.__getLayer(self.comTerrain, self.rasterLayers)

    def getRoadLayer(self):
        return self.__getLayer(self.comRoad, self.roadLayers)

    def getAntennaLayer(self):
        return self.__getLayer(self.comAntenna, self.antennaLayers)