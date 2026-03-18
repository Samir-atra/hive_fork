import json
from unittest.mock import MagicMock, patch

from framework.runner.tool_registry import ToolRegistry


def test_discover_declarative_python_tool(tmp_path):
    # Create a temporary python module
    module_dir = tmp_path / "test_module"
    module_dir.mkdir()

    module_file = module_dir / "my_funcs.py"
    module_file.write_text(
        "def test_func(text: str, count: int = 1):\n"
        "    return {'result': text * count}\n"
    )

    # Add module_dir to sys.path so it can be imported
    import sys
    sys.path.insert(0, str(module_dir))

    # Create a tools directory
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create declarative tool definition
    yaml_content = """
name: repeat_text
description: Repeat text a given number of times
exec:
  type: python_function
  module: my_funcs
  function: test_func
inputs:
  - name: text
    type: str
  - name: count
    type: int
    default: 1
"""
    (tools_dir / "tool.yaml").write_text(yaml_content)

    registry = ToolRegistry()
    count = registry.discover_from_declarative_dir(tools_dir)
    assert count == 1

    tools = registry.get_tools()
    assert "repeat_text" in tools
    tool = tools["repeat_text"]
    assert tool.description == "Repeat text a given number of times"
    assert "text" in tool.parameters["properties"]
    assert "count" in tool.parameters["properties"]

    executor = registry.get_executor()

    from framework.llm.provider import ToolResult, ToolUse
    tool_use = ToolUse(id="1", name="repeat_text", input={"text": "hello", "count": 2})
    result = executor(tool_use)

    assert isinstance(result, ToolResult)
    content = json.loads(result.content)
    assert content["result"] == "hellohello"

    # Cleanup
    sys.path.remove(str(module_dir))


def test_discover_declarative_shell_tool(tmp_path):
    # Create a tools directory
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create declarative tool definition
    json_content = {
        "name": "echo_tool",
        "description": "Echoes text",
        "exec": {
            "type": "shell",
            "command": 'python -c "import os; print(os.environ.get(\'TEXT_TO_ECHO\', \'\'))"'
        },
        "inputs": [
            {
                "name": "text_to_echo",
                "type": "str"
            }
        ]
    }
    (tools_dir / "tool.json").write_text(json.dumps(json_content))

    registry = ToolRegistry()
    count = registry.discover_from_declarative_dir(tools_dir)
    assert count == 1

    tools = registry.get_tools()
    assert "echo_tool" in tools

    executor = registry.get_executor()

    from framework.llm.provider import ToolUse
    tool_use = ToolUse(id="1", name="echo_tool", input={"text_to_echo": "hello_world"})
    result = executor(tool_use)

    content = json.loads(result.content)
    # The output should contain 'hello_world'
    assert "hello_world" in content["stdout"]

def test_discover_declarative_http_tool(tmp_path):
    # Create a tools directory
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create declarative tool definition for multiple tools in a file
    yaml_content = """
type: http
tools:
  - name: get_user
    description: Get user by ID
    api: http://example.com/api/users/<user_id>
    method: GET
    inputs:
      - name: user_id
        type: int
exec:
  type: http
"""
    (tools_dir / "tool.yaml").write_text(yaml_content)

    registry = ToolRegistry()
    count = registry.discover_from_declarative_dir(tools_dir)
    assert count == 1

    tools = registry.get_tools()
    assert "get_user" in tools

    executor = registry.get_executor()

    from framework.llm.provider import ToolResult, ToolUse
    tool_use = ToolUse(id="1", name="get_user", input={"user_id": 123})

    # Mock urllib.request.urlopen
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"id": 123, "name": "Test User"}'

    mock_response.__enter__.return_value = mock_response
    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        result = executor(tool_use)

        assert isinstance(result, ToolResult)
        content = json.loads(result.content)
        assert content["name"] == "Test User"
        assert content["id"] == 123

        # Verify URL construction
        args, kwargs = mock_urlopen.call_args
        request = args[0]
        assert request.full_url == "http://example.com/api/users/123"
        assert request.method == "GET"
