from osgeo import osr, gdal, ogr
from qgis.core import *

class RasterLayer:

    def __init__(self, layer):
        self.layer = layer
        self.raster = gdal.Open(layer.source())
        self.cols = self.raster.RasterXSize
        self.rows = self.raster.RasterYSize
        self.band = self.raster.GetRasterBand(1)
        self.geotransform = self.raster.GetGeoTransform()
        self.data = self.band.ReadAsArray(0, 0, self.cols, self.rows)

    def srid(self):
        return int(str(self.layer.crs().authid()).split(":")[1])

    def findCellSizeInMeters(self):

        bag_gtrn = self.geotransform
        bag_proj = self.raster.GetProjectionRef()
        bag_srs = osr.SpatialReference(bag_proj)
        geo_srs = bag_srs.CloneGeogCS()
        transform = osr.CoordinateTransformation( bag_srs, geo_srs)

        point1=(0,0)
        point2=(0,1)

        x1 = bag_gtrn[0] + bag_gtrn[1] * point1[0] + bag_gtrn[2] * point1[1]
        y1 = bag_gtrn[3] + bag_gtrn[4] * point1[0] + bag_gtrn[5] * point1[1]
        x2 = bag_gtrn[0] + bag_gtrn[1] * point2[0] + bag_gtrn[2] * point2[1]
        y2 = bag_gtrn[3] + bag_gtrn[4] * point2[0] + bag_gtrn[5] * point2[1]  

        point1 = transform.TransformPoint(x1, y1)[:2]
        point2 = transform.TransformPoint(x2, y2)[:2]
        firstpoint = QgsPoint(point1[0],point1[1])
        secondpoint = QgsPoint(point2[0],point2[1])

        #Create a measure object
        distance = QgsDistanceArea()
        crs = QgsCoordinateReferenceSystem()
        crs.createFromSrsId(3452) # EPSG:4326
        distance.setSourceCrs(crs)
        distance.setEllipsoidalMode(True)
        distance.setEllipsoid('WGS84')

        return int(round(distance.measureLine(firstpoint, secondpoint)))