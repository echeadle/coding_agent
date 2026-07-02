import os
import tempfile
import pytest
from nanocode import (
    Agent, AgentStop, Thought, ToolCall, ToolContext, Memory,
    ReadFile, WriteFile, SaveMemory, get_tool, tool_definitions, tools,
)


# --- Fake Brain for Testing ---

class FakeBrain:
    """Fake brain for testing - returns predictable responses."""

    def __init__(self, responses=None, memory=None, tools=None):
        self.memory = memory
        self.tools = tools or []
        self.responses = responses or [Thought(text="Fake response", raw_content=[{"type": "text", "text": "Fake response"}])]
        self.call_count = 0

    def think(self, conversation):
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return Thought(text="No more responses", raw_content=[{"type": "text", "text": "No more responses"}])


# --- Tests from previous chapters ---

def test_quit_command_raises_agent_stop():
    """Verify /q raises AgentStop exception."""
    agent = Agent(brain=FakeBrain(), tools=tools)
    with pytest.raises(AgentStop):
        agent.handle_input("/q")


def test_empty_input_returns_empty_string():
    """Verify empty/whitespace input returns empty string."""
    agent = Agent(brain=FakeBrain(), tools=tools)
    assert agent.handle_input("") == ""
    assert agent.handle_input("   ") == ""


def test_handle_input_returns_brain_response():
    """Verify handle_input returns the brain's response text."""
    brain = FakeBrain(responses=[
        Thought(text="Hello!", raw_content=[{"type": "text", "text": "Hello!"}])
    ])
    agent = Agent(brain=brain, tools=tools)
    result = agent.handle_input("hi")
    assert result == "Hello!"


# --- Tool class tests (updated for ToolContext) ---

def test_read_file_adds_line_numbers():
    """Verify ReadFile prefixes each line with line numbers."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("line one\nline two\nline three\n")
        temp_path = f.name

    try:
        tool = ReadFile()
        context = ToolContext()
        result = tool.execute(context, temp_path)
        assert "1 | line one" in result
        assert "2 | line two" in result
    finally:
        os.unlink(temp_path)


def test_read_file_handles_missing_file():
    """Verify ReadFile returns error for missing file."""
    tool = ReadFile()
    context = ToolContext()                                  # added ToolContext
    result = tool.execute(context, "/nonexistent/path/file.txt")
    assert "Error" in result


def test_write_file_creates_file():
    """Verify WriteFile creates a file with content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.txt")
        tool = WriteFile()
        context = ToolContext()
        result = tool.execute(context, path, "hello world")

        assert os.path.exists(path)
        assert "Successfully wrote" in result


def test_write_file_overwrites_existing():
    """Verify WriteFile overwrites existing content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.txt")
        tool = WriteFile()
        context = ToolContext()                              # added ToolContext

        tool.execute(context, path, "original content")
        tool.execute(context, path, "new content")

        with open(path) as f:
            assert f.read() == "new content"


def test_write_file_handles_bad_path():
    """Verify WriteFile returns error for invalid path."""
    tool = WriteFile()
    context = ToolContext()                                  # added ToolContext
    result = tool.execute(context, "/nonexistent/path/file.txt", "content")
    assert "Error" in result


# --- Tool definition tests ---

def test_tool_has_required_attributes():
    """Verify tool classes have name, description, input_schema."""
    tool = ReadFile()
    assert tool.name == "read_file"
    assert tool.description is not None
    assert tool.input_schema is not None


def test_get_tool_finds_by_name():
    """Verify get_tool finds a tool by name."""
    tool = get_tool(tools, "read_file")
    assert tool is not None
    assert tool.name == "read_file"


def test_get_tool_returns_none_for_unknown():
    """Verify get_tool returns None for unknown tool name."""
    tool = get_tool(tools, "unknown_tool")
    assert tool is None


def test_tool_definitions_for_api():
    """Verify tool_definitions returns correct format for API."""
    defs = tool_definitions(tools)
    assert len(defs) == 3                                    # updated: ReadFile, WriteFile, SaveMemory
    for d in defs:
        assert "name" in d
        assert "description" in d
        assert "input_schema" in d
        assert "execute" not in d


# --- Memory class tests ---

def test_memory_creates_default_file():
    """Verify Memory creates file with default content if missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "memory.md")
        memory = Memory(path=path)

        assert os.path.exists(path)
        assert "Nanocode" in memory.content


def test_memory_loads_existing_content():
    """Verify Memory loads content from existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "memory.md")

        with open(path, 'w') as f:
            f.write("Custom memory content")

        memory = Memory(path=path)
        assert memory.content == "Custom memory content"


def test_memory_save_updates_content_and_file():
    """Verify Memory.save() updates both content and file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "memory.md")
        memory = Memory(path=path)

        memory.save("New content")

        assert memory.content == "New content"
        with open(path) as f:
            assert f.read() == "New content"


# --- SaveMemory tool tests ---

def test_save_memory_updates_memory():
    """Verify SaveMemory updates the Memory object."""
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = Memory(path=os.path.join(tmpdir, "memory.md"))
        tool = SaveMemory()
        context = ToolContext(memory=memory)

        result = tool.execute(context, "Updated preferences")

        assert "successfully" in result.lower()
        assert memory.content == "Updated preferences"


def test_save_memory_fails_without_memory():
    """Verify SaveMemory returns error when memory is None."""
    tool = SaveMemory()
    context = ToolContext(memory=None)
    result = tool.execute(context, "test")
    assert "Error" in result


# --- Agent tool execution tests ---

def test_agent_execute_tool_finds_tool():
    """Verify agent can execute a registered tool."""
    agent = Agent(brain=FakeBrain(), tools=tools)
    result = agent._execute_tool("read_file", {"path": __file__})
    assert "import" in result


def test_agent_execute_tool_unknown_tool():
    """Verify agent returns error for unknown tool."""
    agent = Agent(brain=FakeBrain(), tools=tools)
    result = agent._execute_tool("unknown_tool", {})
    assert "not found" in result


def test_agent_tools_definitions():
    """Verify tool definitions include all tools."""
    agent = Agent(brain=FakeBrain(), tools=tools)
    definitions = tool_definitions(agent.tools)

    tool_names = [d["name"] for d in definitions]
    assert "save_memory" in tool_names
    assert "read_file" in tool_names
    assert "write_file" in tool_names


# --- Agent with Memory tests ---

def test_agent_has_save_memory_tool():
    """Verify agent has save_memory tool."""
    agent = Agent(brain=FakeBrain(), tools=tools)
    tool_names = [t.name for t in agent.tools]
    assert "save_memory" in tool_names


def test_agent_execute_save_memory_tool():
    """Verify save_memory tool updates the Memory object through agent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = Memory(path=os.path.join(tmpdir, "memory.md"))
        agent = Agent(brain=FakeBrain(), tools=tools, memory=memory)

        result = agent._execute_tool("save_memory", {"content": "Updated preferences"})

        assert "successfully" in result.lower()
        assert memory.content == "Updated preferences"


def test_brain_receives_memory_content():
    """Verify brain has access to memory content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = Memory(path=os.path.join(tmpdir, "memory.md"))
        memory.save("Custom system prompt")

        brain = FakeBrain(memory=memory)
        assert brain.memory.content == "Custom system prompt"


# --- Agentic loop tests ---

def test_agentic_loop_executes_tool_calls():
    """Verify agentic loop executes tool calls and continues.
    Note: ToolContext is created internally by Agent._execute_tool —
    this test does not need to change from Ch05."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test content\n")
        temp_path = f.name

    try:
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
        assert brain.call_count == 2
    finally:
        os.unlink(temp_path)


def test_thought_stores_raw_content():
    """Verify Thought stores raw_content for message history."""
    raw = [{"type": "text", "text": "Hello"}]
    thought = Thought(text="Hello", raw_content=raw)
    assert thought.raw_content == raw
    
# --- Chapter 7 tests

def test_agent_defaults_to_plan_mode():
    """Verify agent starts in plan mode by default."""
    agent = Agent(brain=FakeBrain(), tools=tools)
    assert agent.mode == "plan"
    
def test_plan_mode_hides_write_file():
    """Verify plan mode des not expose write_file to the brain."""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="plan")
    tool_names = [t["name"] for t in agent.brain.tools]
    
    assert "write_file" not in tool_names
    assert "write_plan" in tool_names
    
def test_act_mode_shows_all_tools():
    """Verify act mode exposes all tools to the brain"""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="act")
    tool_names = [t["name"] for t in agent.brain.tools]
    
    assert "write_file" in tool_names
    
def test_mode_command_switches_to_act():
    """Verify /mode act switches to act mode."""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="plan")
    result = agent.handle_input("/mode act")
    
    assert agent.mode == "act"
    assert "ACT" in result