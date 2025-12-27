#!/usr/bin/env python3
"""
Multi-Agent MCP Server
Integrates local LLMs (Continue), Codex CLI, and Gemini CLI
"""

import asyncio
import json
import subprocess
import sys
from typing import Any

import httpx

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
except ImportError:
    print("MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)


server = Server("multi-agent")

# Local LLM endpoints (from Continue config)
LOCAL_MODELS = {
    "qwen3-coder": {
        "base_url": "http://localhost:8003",
        "model": "qwen3-coder",
        "description": "Qwen3-Coder-30B for code generation and editing",
    },
    "gpt-oss": {
        "base_url": "http://localhost:8004",
        "model": "gpt-oss-20b",
        "description": "GPT-OSS-20B with tool use and autocomplete",
        "context_length": 20000,
        "max_tokens": 8192,
    },
}


async def call_local_llm(
    model_key: str,
    prompt: str,
    system: str = "",
    max_tokens: int = 4096,
) -> str:
    """Call local LLM via OpenAI-compatible API"""
    config = LOCAL_MODELS.get(model_key)
    if not config:
        return f"Error: Unknown model '{model_key}'. Available: {list(LOCAL_MODELS.keys())}"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": config["model"],
        "messages": messages,
        "max_tokens": min(max_tokens, config.get("max_tokens", 4096)),
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{config['base_url']}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        return f"Error: Request to {model_key} timed out"
    except Exception as e:
        return f"Error calling {model_key}: {str(e)}"


def run_codex_cli(command: str, args: list[str], input_text: str = "") -> str:
    """Run Codex CLI command"""
    cmd = ["codex", command] + args

    try:
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Codex command timed out (5min limit)"
    except Exception as e:
        return f"Error running Codex: {str(e)}"


def run_gemini_cli(prompt: str, model: str = "gemini-3-flash") -> str:
    """Run Gemini via Python SDK (requires GOOGLE_API_KEY env)"""
    script = f'''
import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))
model = genai.GenerativeModel("{model}")
response = model.generate_content("""{prompt.replace('"', '\\"')}""")
print(response.text)
'''
    try:
        result = subprocess.run(
            ["python3", "-c", script],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        return result.stdout or "(no output)"
    except Exception as e:
        return f"Error running Gemini: {str(e)}"


# Tool definitions
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="local_qwen_coder",
            description="Use Qwen3-Coder-30B (local) for code generation, editing, and analysis. Best for sensitive code that shouldn't leave the machine.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The coding task or question"},
                    "system": {"type": "string", "description": "Optional system prompt", "default": ""},
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="local_gpt_oss",
            description="Use GPT-OSS-20B (local) for general tasks with tool use. Good for security-sensitive operations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The task or question"},
                    "system": {"type": "string", "description": "Optional system prompt", "default": ""},
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="codex_review",
            description="Use OpenAI Codex CLI to review code. Provides detailed code analysis and suggestions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to review"},
                    "context": {"type": "string", "description": "Additional context about the code", "default": ""},
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="codex_exec",
            description="Use OpenAI Codex CLI to execute a coding task non-interactively.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The coding task to execute"},
                    "writable_root": {"type": "string", "description": "Directory Codex can write to", "default": "."},
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="gemini_research",
            description="Use Google Gemini for web research and information gathering. Good for documentation lookup and general knowledge.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Research query or question"},
                    "model": {
                        "type": "string",
                        "description": "Gemini model to use",
                        "default": "gemini-3-flash",
                        "enum": ["gemini-3-flash", "gemini-3-pro", "gemini-2.5-pro", "gemini-2.5-flash"],
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    result = ""

    if name == "local_qwen_coder":
        result = await call_local_llm(
            "qwen3-coder",
            arguments["prompt"],
            arguments.get("system", "You are an expert programmer."),
        )

    elif name == "local_gpt_oss":
        result = await call_local_llm(
            "gpt-oss",
            arguments["prompt"],
            arguments.get("system", ""),
        )

    elif name == "codex_review":
        code = arguments["code"]
        context = arguments.get("context", "")
        input_text = f"Context: {context}\n\nCode:\n{code}" if context else code
        result = run_codex_cli("review", [], input_text)

    elif name == "codex_exec":
        prompt = arguments["prompt"]
        writable_root = arguments.get("writable_root", ".")
        result = run_codex_cli("exec", ["--writable-root", writable_root, prompt], "")

    elif name == "gemini_research":
        result = run_gemini_cli(
            arguments["query"],
            arguments.get("model", "gemini-3-flash"),
        )

    else:
        result = f"Unknown tool: {name}"

    return [TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
