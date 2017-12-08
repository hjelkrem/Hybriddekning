class RasterCounter:

    def __init__(self):
        self.inside = 0
        self.outside = 0

    def hasOutsiders(self):
        return self.outside > 0

    def sum(self):
        return self.inside + self.outside