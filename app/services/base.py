
"""
Base service functionality
"""

class BaseService:
    def __init__(self):
        pass
    
    def process(self, data):
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement process method")
