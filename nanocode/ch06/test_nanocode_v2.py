import os
import tempfile
import pytest
from nanocode import (
    Agent, AgentStop, Thought, ToolCall,Brain, BRAINS,
    ReadFile, WriteFile, get_tool, tool_definitions, tools,
)


# --- Fake Brain for Testing ---

class FakeBrain(Brain):
    """Fake brain for testing - returns predictable responses."""

    def __init__(self, responses=None, tools=None):
        self.responses = responses or [Thought(text="Fake response")]
        self.call_count = 0
        self.last_conversation = None

    def think(self, conversation):
        self.last_conversation = list(conversation)
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return Thought(text="No more responses")


# --- Tests from previous chapters ---

def test_quit_command_raises_agent_stop():
    """Verify /q raises AgentStop exception."""
    agent = Agent(brain=FakeBrain())
    with pytest.raises(AgentStop):
        agent.handle_input("/q")


def test_empty_input_returns_empty_string():
    """Verify empty/whitespace input returns empty string."""
    agent = Agent(brain=FakeBrain())
    assert agent.handle_input("") == ""
    assert agent.handle_input("   ") == ""


def test_handle_input_returns_brain_response():
    """Verify handle_input returns the brain's response text."""
    brain = FakeBrain(responses=[Thought(text="Hello from brain!")])
    agent = Agent(brain=brain)
    result = agent.handle_input("hi")
    assert result == "Hello from brain!"


def test_conversation_accumulates():
    """Verify conversation list grows with each interaction."""
    brain = FakeBrain(responses=[
        Thought(text="Response 1"),
        Thought(text="Response 2")
    ])
    agent = Agent(brain=brain)

    agent.handle_input("First message")
    assert len(agent.conversation) == 2  # user + assistant

    agent.handle_input("Second message")
    assert len(agent.conversation) == 4  # 2 users + 2 assistants


# --- New tests for Chapter 4: Multiple Brains ---

def test_agent_stores_brain_name():
    """Verify agent stores the brain name."""
    agent = Agent(brain=FakeBrain(), brain_name="claude")
    assert agent.brain_name == "claude"

    agent = Agent(brain=FakeBrain(), brain_name="deepseek")
    assert agent.brain_name == "deepseek"


def test_brains_registry_has_expected_providers():
    """Verify BRAINS registry contains expected providers."""
    assert "claude" in BRAINS
    assert "deepseek" in BRAINS


def test_switch_command_toggles_brain_name():
    """Verify /switch updates brain_name (using FakeBrain for both)."""
    agent = Agent(brain=FakeBrain(), brain_name="claude", tools=[])

    # Mock BRAINS to use FakeBrain for switching
    original_brains = BRAINS.copy()
    BRAINS["claude"] = FakeBrain
    BRAINS["deepseek"] = FakeBrain

    try:
        result = agent.handle_input("/switch")
        assert "deepseek" in result
        assert agent.brain_name == "deepseek"

        result = agent.handle_input("/switch")
        assert "claude" in result
        assert agent.brain_name == "claude"
    finally:
        BRAINS.clear()
        BRAINS.update(original_brains)


def test_thought_with_text():
    """Verify Thought stores text."""
    thought = Thought(text="Hello")
    assert thought.text == "Hello"
    assert thought.tool_calls == []


def test_thought_with_tool_calls():
    """Verify Thought stores tool calls."""
    calls = [ToolCall(id="1", name="read_file", args={"path": "test.txt"})]
    thought = Thought(text="Let me read that", tool_calls=calls)
    assert thought.text == "Let me read that"
    assert len(thought.tool_calls) == 1
    assert thought.tool_calls[0].name == "read_file"


def test_tool_call_stores_attributes():
    """Verify ToolCall stores id, name, and args."""
    call = ToolCall(id="abc123", name="write_file", args={"path": "x.txt", "content": "hi"})
    assert call.id == "abc123"
    assert call.name == "write_file"
    assert call.args["path"] == "x.txt"
    
def test_tool_has_required_attributes():
    """Verify tool classes have name, description, input_schema."""
    tool = ReadFile()
    assert tool.name == "read_file"
    assert tool.description is not None
    assert tool.input_schema is not None
    
def test_read_file_adds_line_numbers():
    """Verify ReadFile prefixes each line with line numbers."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("line one\nline two\nline three\n")
        temp_path = f.name
        
    try:
        tool = ReadFile()
        result = tool.execute(temp_path)
        assert "1 | line one" in result
        assert "2 | line two" in result
        assert "3 | line three" in result
    finally:
        os.unlink(temp_path)
        
def test_write_file_creates_file():
    """Verify WriteFile creates a file with content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "text.txt")
        tool = WriteFile()
        result = tool.execute(path, "hello world")
        
        assert os.path.exists(path)
        assert "Successfully wrote" in result
        with open(path) as f:
            assert f.read() == "hello world"
            
# --- Agentic loop tests ---

def test_agentic_loop_executes_tool_calls():
    """Verify agentic loop executes tool calls and continues."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test content")
        temp_path = f.name

    try:
        # Brain returns a tool call, then a final response
        brain = FakeBrain(responses=[
            Thought(
                text="Let me read that file.",
                tool_calls=[ToolCall(id="1", name="read_file", args={"path": temp_path})],
                raw_content=[
                    {"type": "text", "text": "Let me read that file."},
                    {"type": "tool_use", "id": "1", "name": "read_file", "input": {"path": temp_path}}
                ]
            ),
            Thought(
                text="The file contains test content.",
                raw_content=[{"type": "text", "text": "The file contains test content."}]
            )
        ])
        agent = Agent(brain=brain, tools=tools)
        result = agent.handle_input("Read the file")

        assert "Let me read that file." in result
        assert "The file contains test content." in result
        assert brain.call_count == 2  # Called twice (tool call + final)
    finally:
        os.unlink(temp_path)