
"""
Base prompt handling functionality
"""

class PromptManager:
    def __init__(self):
        self.prompts = {}
    
    def add_prompt(self, name: str, template: str):
        """Add a prompt template"""
        self.prompts[name] = template
    
    def get_prompt(self, name: str, **kwargs) -> str:
        """Get and format a prompt template"""
        if name not in self.prompts:
            raise ValueError(f"Prompt '{name}' not found")
        return self.prompts[name].format(**kwargs)
