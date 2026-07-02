import os
import tempfile
import pytest
from nanocode import (
    Agent, AgentStop, Thought, ToolCall, ToolContext, Memory,
    ReadFile, WriteFile, WritePlan, ListFiles, SearchCodebase, SaveMemory,
    get_tool, tool_definitions, tools,
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


def test_read_file_adds_line_numbers():
    """Verify ReadFile prefixes each line with line numbers."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("line one\nline two\n")
        temp_path = f.name

    try:
        tool = ReadFile()
        context = ToolContext()
        result = tool.execute(context, temp_path)
        assert "1 | line one" in result
        assert "2 | line two" in result
    finally:
        os.unlink(temp_path)


# --- Mode tests ---

def test_agent_defaults_to_plan_mode():
    """Verify agent starts in plan mode by default."""
    agent = Agent(brain=FakeBrain(), tools=tools)
    assert agent.mode == "plan"


def test_agent_can_start_in_act_mode():
    """Verify agent can be initialized in act mode."""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="act")
    assert agent.mode == "act"


def test_mode_command_switches_to_act():
    """Verify /mode act switches to act mode."""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="plan")
    result = agent.handle_input("/mode act")

    assert agent.mode == "act"
    assert "ACT" in result


def test_mode_command_switches_to_plan():
    """Verify /mode plan switches to plan mode."""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="act")
    result = agent.handle_input("/mode plan")

    assert agent.mode == "plan"
    assert "PLAN" in result


def test_mode_command_defaults_to_plan():
    """Verify /mode without argument defaults to plan mode."""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="act")
    result = agent.handle_input("/mode")

    assert agent.mode == "plan"


# --- Tool filtering by mode ---

def test_plan_mode_hides_write_file():
    """Verify plan mode does not expose write_file to the brain."""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="plan")
    tool_names = [t["name"] for t in agent.brain.tools]

    assert "write_file" not in tool_names
    assert "write_plan" in tool_names
    assert "read_file" in tool_names


def test_act_mode_shows_all_tools():
    """Verify act mode exposes all tools to the brain."""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="act")
    tool_names = [t["name"] for t in agent.brain.tools]

    assert "write_file" in tool_names
    assert "write_plan" in tool_names
    assert "read_file" in tool_names


def test_mode_switch_updates_brain_tools():
    """Verify switching mode changes the brain's tool menu."""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="plan")

    # Plan mode: no write_file
    plan_names = [t["name"] for t in agent.brain.tools]
    assert "write_file" not in plan_names

    # Switch to act: write_file appears
    agent.handle_input("/mode act")
    act_names = [t["name"] for t in agent.brain.tools]
    assert "write_file" in act_names

    # Switch back to plan: write_file disappears
    agent.handle_input("/mode plan")
    plan_names = [t["name"] for t in agent.brain.tools]
    assert "write_file" not in plan_names


# --- WritePlan tool ---

def test_write_plan_saves_file():
    """Verify WritePlan writes to PLAN.md."""
    original_dir = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            tool = WritePlan()
            context = ToolContext()
            result = tool.execute(context, content="# My Plan\n\nStep 1: Read code")

            assert "Plan saved" in result
            assert os.path.exists("PLAN.md")
            with open("PLAN.md") as f:
                assert f.read() == "# My Plan\n\nStep 1: Read code"
        finally:
            os.chdir(original_dir)


# --- WriteFile tool (no mode checks, always works) ---

def test_write_file_writes_file():
    """Verify WriteFile writes content to the given path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.py")
        tool = WriteFile()
        context = ToolContext()

        result = tool.execute(context, file_path, "print('hello')")

        assert "Successfully wrote" in result
        assert os.path.exists(file_path)


# --- Agent has all tools ---

def test_agent_has_all_tools():
    """Verify agent has all tools for execution."""
    agent = Agent(brain=FakeBrain(), tools=tools)
    tool_names = [t.name for t in agent.tools]
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "write_plan" in tool_names
    assert "save_memory" in tool_names

# --- Chapter 8 ---

def test_list_files_returns_file_tree():
    """Verify ListFiles returns a tree structure"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"))
        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write("# Test")
        with open(os.path.join(tmpdir, "src", "main.py"), 'w') as f:
            f.write("print('hello)")
            
        tool = ListFiles()
        context = ToolContext()
        result = tool.execute(context, path=tmpdir)
        
        assert "README.md" in result
        assert "src/" in result
        assert "main.py" in result

def test_list_files_skips_git_and_pycache():
    """Verify ListFiles skips .git and __pycache__ directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directories that should be skipped
        os.makedirs(os.path.join(tmpdir, ".git"))
        os.makedirs(os.path.join(tmpdir, "__pycache__"))
        os.makedirs(os.path.join(tmpdir, "src"))

        with open(os.path.join(tmpdir, ".git", "config"), 'w') as f:
            f.write("git config")
        with open(os.path.join(tmpdir, "__pycache__", "cache.pyc"), 'w') as f:
            f.write("cache")
        with open(os.path.join(tmpdir, "src", "main.py"), 'w') as f:
            f.write("print('hello')")

        tool = ListFiles()
        context = ToolContext()
        result = tool.execute(context, path=tmpdir)

        assert "config" not in result
        assert "cache.pyc" not in result
        assert "main.py" in result
        
def test_search_codebase_finds_matches():
    """Verify SearchCodebase finds text in files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "test.py"), 'w') as f:
            f.write("def hello_world():\n   print('hello')\n")
            
        tool = SearchCodebase()
        context = ToolContext()
        result = tool.execute(context, query="hello_world", path=tmpdir)
        
        assert "test.py" in result
        assert "hello_world" in result
        assert ":1:" in result  # Line number
        
def test_search_codebase_case_insensitive():
    """Verify SearchCodebase is case-insensitive."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "test.py"), 'w') as f:
            f.write("def HelloWorld():\n    pass\n")

        tool = SearchCodebase()
        context = ToolContext()
        result = tool.execute(context, query="helloworld", path=tmpdir)
        assert "HelloWorld" in result