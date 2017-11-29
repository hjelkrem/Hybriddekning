class Antenna:

	def __init__(self, id, frequency, height, point):

		self.id = id
		self.frequency = frequency
		self.frequencyHz = frequency * 1000000
		self.height = height
		self.point = point

	@staticmethod
	def fromFeatures(features):

		antennas = []

		for feature in features:
			attrs = feature.attributes()
			antennas.append(Antenna(attrs[0], attrs[1], attrs[2], feature.geometry().asPoint()))

		return antennas
