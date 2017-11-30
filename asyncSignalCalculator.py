class AsyncSignalCalculator:

    def __init__(self, owner, cellSizeInMeters, filearray, rasterHeights, validAntennas, minx, miny, roadpoints, threadCount):
        self.owner = owner
        self.cellSizeInMeters = cellSizeInMeters
        self.filearray = filearray
        self.rasterHeights = rasterHeights
        self.validAntennas = validAntennas
        self.minx = minx
        self.miny = miny
        self.roadpoints = roadpoints
        self.threadCount = threadCount

        self.takePoint = 0
        self.totalCount = len(self.roadpoints)
        self.lock = threading.Lock()

    def calculateAPoint(self):

        with self.lock:
            
            roadpoint = self.roadpoints[self.takePoint]

            self.takePoint += 1
            
            if self.takePoint >= self.totalCount:
                return False
        
        foundSignal, value = self.owner.calculateSignalAtPoint(self.cellSizeInMeters, self.rasterHeights, self.validAntennas, roadpoint)

        if foundSignal:
            with self.lock:
                self.filearray[int(roadpoint[1]-self.miny)][int(roadpoint[0]-self.minx)] = value

        return True

    def workThroughThePoints(self):
        while True:
            if not self.calculateAPoint():
                break

    def run(self):

        threads = []
        for i in range(self.threadCount):
            t = threading.Thread(target=self.workThroughThePoints)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()