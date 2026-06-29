# --- Exceptions ---

class AgentStop(Exception):
    """Raised when the agent should stop processing"""
    pass




class Agent:
    """A coding agent that processes user input."""
    
    def __init__(self):
        pass
    
    def handle_input(self, user_input):
        """Handle user input. Returns output string, raises AgentStop to quit."""
        if user_input.strip() == "/q":
            raise AgentStop()
        
        if not user_input.strip():
            return ""
        
        return f"You said: {user_input}\n(Agent not yet connected)"
