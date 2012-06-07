class DummyCursor:
    def __init__(self):
        self.rowcount = 0
        self.rowContent = []
        
    def execute(self, instructions):
        return
    
    #def rowcount(self):
     #   return int(self.numRows)
    
    def fetchall(self):
        return self.rowContent