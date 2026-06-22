class RichDashboard:
    def __init__(self,*a,**k): self.events=[]
    def handle_event(self,event): self.events.append(event)
