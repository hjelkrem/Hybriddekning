import time

class Timing:

	def __init__(self):

		self.dict = {}
		self.start()

	def start(self):
		self.timestamp = time.clock()

	def time(self, entry):

		newTime = time.clock()
		delta = newTime - self.timestamp

		if entry not in self.dict:
			self.dict[entry] = 0
		self.dict[entry] += delta * 1000

		self.timestamp = newTime