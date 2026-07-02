# Plan: Add SearchWeb Tool to nanocode.py

## Overview
Add a `SearchWeb` tool class that queries DuckDuckGo's free HTML search endpoint and
returns a list of organic results (title, URL, snippet) to the agent.

## Approach

### 1. HTTP strategy
DuckDuckGo has no public API key requirement. We'll use the **HTML endpoint**:
`https://html.duckduckgo.com/html/?q=<query>`
and parse the response with the stdlib `html.parser` (no extra deps).

### 2. New `SearchWeb` class (after `RunCommand`, before Tool Helpers)
- `name = "search_web"`
- `plan_safe = True` — read-only, safe in plan mode
- `input_schema`: `query` (required string), `max_results` (optional int, default 5)
- `execute()`:
  1. GET the DuckDuckGo HTML page with a browser-like `User-Agent`
  2. Parse `<a class="result__a">` anchors (title + href) and
     `<a class="result__snippet">` spans for snippets
  3. Return formatted markdown list of results, or an error string

### 3. Register the tool
- Add `SearchWeb()` to the `tools` list at line 528.

### 4. Tests (in `test_nanocode.py`)
- Import `SearchWeb`
- `test_search_web_is_plan_safe` — `plan_safe` is True
- `test_search_web_returns_results` — mock `requests.get`, verify formatted output
- `test_search_web_no_results` — mock returns empty body, verify graceful message
- `test_search_web_network_error` — mock raises exception, verify error string
- `test_agent_has_search_web_tool` — `search_web` present in agent tool names
- `test_search_web_in_plan_mode` — `search_web` exposed to brain in plan mode
