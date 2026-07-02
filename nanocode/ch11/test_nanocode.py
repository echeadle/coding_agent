import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest
from nanocode import (
    Agent, AgentStop, Thought, ToolCall, ToolContext, Memory, EditFile,
    ReadFile, WriteFile, WritePlan, ListFiles, SearchCodebase, SaveMemory, RunCommand, SearchWeb,
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
        
# --- Chapter 9 ---

def test_run_command_handles_nonexistent_command():
    """Verify run_command handles commands that don't exist."""
    tool = RunCommand()
    context = ToolContext()
    result = tool.execute(context, command="nonexistent_command_xyz_12345")

    # Should have some error output (either STDERR or Error message)
    assert "STDERR" in result or "Error" in result or "not found" in result.lower()


def test_run_command_runs_python():
    """Verify run_command can run Python scripts."""
    tool = RunCommand()
    context = ToolContext()
    result = tool.execute(context, command="python -c \"print('hello from python')\"")

    assert "hello from python" in result


def test_agent_has_run_command_tool():
    """Verify agent has run_command tool."""
    agent = Agent(brain=FakeBrain(), tools=tools)
    tool_names = [t.name for t in agent.tools]
    assert "run_command" in tool_names


def test_agent_execute_run_command():
    """Verify agent can execute run_command."""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="act")
    result = agent._execute_tool("run_command", {"command": "echo test"})

    assert "test" in result


def test_tool_definitions_includes_run_command():
    """Verify tool_definitions includes run_command."""
    defs = tool_definitions(tools)
    tool_names = [d["name"] for d in defs]
    assert "run_command" in tool_names
    
# --- EditFile Tests ---

def test_edit_file_replaces_text():
    """Verify EditFile replaces text in a file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("x = 1\ny = 2\nz = 3\n")
        temp_path = f.name

    try:
        tool = EditFile()
        context = ToolContext()
        result = tool.execute(context, temp_path, "y = 2", "y = 42")

        assert "Successfully" in result
        with open(temp_path) as f:
            content = f.read()
        assert "y = 42" in content
        assert "y = 2" not in content
    finally:
        os.unlink(temp_path)


# --- SearchWeb Tests ---

# Minimal DuckDuckGo-style HTML with two results
_SAMPLE_DDG_HTML = """
<html><body>
  <a class="result__a" href="https://example.com/page1">First Result</a>
  <a class="result__snippet" href="#">A brief description of page one.</a>
  <a class="result__a" href="https://example.com/page2">Second Result</a>
  <a class="result__snippet" href="#">A brief description of page two.</a>
</body></html>
"""


def _mock_response(html: str, status_code: int = 200):
    """Build a mock requests.Response with the given HTML body."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_search_web_is_plan_safe():
    """Verify SearchWeb.plan_safe is True (read-only tool)."""
    assert SearchWeb.plan_safe is True


def test_search_web_returns_results():
    """Verify SearchWeb parses titles, URLs and snippets from DuckDuckGo HTML."""
    tool = SearchWeb()
    context = ToolContext()

    with patch("requests.get", return_value=_mock_response(_SAMPLE_DDG_HTML)):
        result = tool.execute(context, query="python testing")

    assert "First Result" in result
    assert "https://example.com/page1" in result
    assert "A brief description of page one." in result
    assert "Second Result" in result
    assert "https://example.com/page2" in result


def test_search_web_respects_max_results():
    """Verify SearchWeb returns at most max_results entries."""
    tool = SearchWeb()
    context = ToolContext()

    with patch("requests.get", return_value=_mock_response(_SAMPLE_DDG_HTML)):
        result = tool.execute(context, query="python", max_results=1)

    assert "First Result" in result
    assert "Second Result" not in result


def test_search_web_no_results():
    """Verify SearchWeb returns a graceful message when no results are found."""
    tool = SearchWeb()
    context = ToolContext()

    with patch("requests.get", return_value=_mock_response("<html><body></body></html>")):
        result = tool.execute(context, query="xyzzy_no_match_expected")

    assert "No results found" in result


def test_search_web_network_error():
    """Verify SearchWeb returns an error string on network failure."""
    import requests as req
    tool = SearchWeb()
    context = ToolContext()

    with patch("requests.get", side_effect=req.exceptions.ConnectionError("timeout")):
        result = tool.execute(context, query="something")

    assert "Error" in result


def test_agent_has_search_web_tool():
    """Verify search_web is present in the agent's tool list."""
    agent = Agent(brain=FakeBrain(), tools=tools)
    tool_names = [t.name for t in agent.tools]
    assert "search_web" in tool_names


def test_search_web_available_in_plan_mode():
    """Verify search_web is exposed to the brain in plan mode (plan_safe=True)."""
    agent = Agent(brain=FakeBrain(), tools=tools, mode="plan")
    brain_tool_names = [t["name"] for t in agent.brain.tools]
    assert "search_web" in brain_tool_names


def test_edit_file_not_found():
    """Verify EditFile returns error when text not found."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("x = 1\n")
        temp_path = f.name

    try:
        tool = EditFile()
        context = ToolContext()
        result = tool.execute(context, temp_path, "not in file", "replacement")

        assert "Error" in result
        assert "Could not find" in result
    finally:
        os.unlink(temp_path)


