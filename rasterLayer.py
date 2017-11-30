from osgeo import osr, gdal, ogr

class RasterLayer:

	def __init__(self, layer):
		self.layer = layer
		self.raster = gdal.Open(layer.source())
		self.band = self.raster.GetRasterBand(1)
		self.geotransform = self.raster.GetGeoTransform()
		self.data = self.band.ReadAsArray(0, 0, self.raster.RasterXSize, self.raster.RasterYSize)

	def srid(self):
		return int(str(self.layer.crs().authid()).split(":")[1])
