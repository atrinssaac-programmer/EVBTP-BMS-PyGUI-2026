import csv
from datetime import datetime
from config import BMSConfig

class BMSLogger:

    def __init__(self):
        self.file=None
        self.writer=None

    def start(self):
        if self.file:
            return

        name=datetime.now().strftime("bms_%Y%m%d_%H%M%S.csv")
        self.file=open(name,"w",newline="")
        self.writer=csv.writer(self.file)

        header=["Time","PackV","PackI","SOC","SOH"]
        header+=[f"C{i+1}" for i in range(BMSConfig.NUM_CELLS)]
        header+=[f"T{i+1}" for i in range(BMSConfig.NUM_TEMPS)]

        self.writer.writerow(header)

    def log(self,data):
        if not self.writer:
            return

        self.writer.writerow([
            datetime.now(),
            data["packV"],
            data["packI"],
            data["soc"],
            data["soh"],
            *data["cells"],
            *data["temps"]
        ])

    def stop(self):
        if self.file:
            self.file.close()
        self.file=None
        self.writer=None
