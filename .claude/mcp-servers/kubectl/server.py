#!/usr/bin/env python3
"""
kubectl MCP Server
Provides structured kubectl operations for Claude Code
"""

import asyncio
import json
import os
import subprocess
import sys
from typing import Any

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
except ImportError:
    print("MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)


server = Server("kubectl")

# Default kubeconfig
KUBECONFIG = os.environ.get("KUBECONFIG", os.path.expanduser("~/.kube/config.home"))


def run_kubectl(args: list[str], timeout: int = 30) -> dict[str, Any]:
    """Run kubectl command and return structured output"""
    env = os.environ.copy()
    env["KUBECONFIG"] = KUBECONFIG

    cmd = ["kubectl"] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {timeout}s",
            "command": " ".join(cmd),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "command": " ".join(cmd),
        }


def parse_json_output(output: str) -> Any:
    """Parse kubectl JSON output"""
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="kubectl_get",
            description="Get Kubernetes resources. Returns structured JSON data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "description": "Resource type (pods, deployments, services, etc.)",
                    },
                    "name": {
                        "type": "string",
                        "description": "Resource name (optional)",
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace (default: all namespaces)",
                    },
                    "selector": {
                        "type": "string",
                        "description": "Label selector (e.g., app=nginx)",
                    },
                    "field_selector": {
                        "type": "string",
                        "description": "Field selector (e.g., status.phase=Running)",
                    },
                },
                "required": ["resource"],
            },
        ),
        Tool(
            name="kubectl_describe",
            description="Describe a Kubernetes resource with detailed info including events.",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "description": "Resource type",
                    },
                    "name": {
                        "type": "string",
                        "description": "Resource name",
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace",
                    },
                },
                "required": ["resource", "name"],
            },
        ),
        Tool(
            name="kubectl_logs",
            description="Get container logs from a pod.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pod": {
                        "type": "string",
                        "description": "Pod name",
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace",
                    },
                    "container": {
                        "type": "string",
                        "description": "Container name (optional)",
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Number of lines from the end (default: 100)",
                        "default": 100,
                    },
                    "previous": {
                        "type": "boolean",
                        "description": "Get logs from previous container instance",
                        "default": False,
                    },
                    "since": {
                        "type": "string",
                        "description": "Only return logs newer than duration (e.g., 1h, 30m)",
                    },
                },
                "required": ["pod", "namespace"],
            },
        ),
        Tool(
            name="kubectl_events",
            description="Get events for troubleshooting. Returns recent cluster events.",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Namespace (optional, default: all)",
                    },
                    "for_resource": {
                        "type": "string",
                        "description": "Filter events for specific resource (e.g., pod/nginx-xxx)",
                    },
                    "types": {
                        "type": "string",
                        "description": "Event types: Normal, Warning (default: all)",
                    },
                },
            },
        ),
        Tool(
            name="kubectl_top",
            description="Show resource usage (CPU/Memory) for nodes or pods.",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "enum": ["nodes", "pods"],
                        "description": "Resource type: nodes or pods",
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace (for pods)",
                    },
                    "selector": {
                        "type": "string",
                        "description": "Label selector",
                    },
                },
                "required": ["resource"],
            },
        ),
        Tool(
            name="kubectl_api_resources",
            description="List available API resources in the cluster.",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_group": {
                        "type": "string",
                        "description": "Filter by API group",
                    },
                    "namespaced": {
                        "type": "boolean",
                        "description": "Filter namespaced resources only",
                    },
                },
            },
        ),
        Tool(
            name="kubectl_get_contexts",
            description="List available kubectl contexts and current context.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="kubectl_cluster_info",
            description="Display cluster information.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    result = {}

    if name == "kubectl_get":
        args = ["get", arguments["resource"], "-o", "json"]

        if arguments.get("name"):
            args.insert(2, arguments["name"])

        if arguments.get("namespace"):
            args.extend(["-n", arguments["namespace"]])
        elif not arguments.get("name"):
            args.append("-A")

        if arguments.get("selector"):
            args.extend(["-l", arguments["selector"]])

        if arguments.get("field_selector"):
            args.extend(["--field-selector", arguments["field_selector"]])

        result = run_kubectl(args)
        if result["success"] and result.get("stdout"):
            parsed = parse_json_output(result["stdout"])
            if parsed:
                result["data"] = parsed
                # Simplify output for readability
                if "items" in parsed:
                    result["count"] = len(parsed["items"])
                    result["summary"] = [
                        {
                            "name": item.get("metadata", {}).get("name"),
                            "namespace": item.get("metadata", {}).get("namespace"),
                            "status": (
                                item.get("status", {}).get("phase")
                                or item.get("status", {}).get("conditions", [{}])[-1].get("type")
                            ),
                        }
                        for item in parsed["items"]
                    ]

    elif name == "kubectl_describe":
        args = ["describe", arguments["resource"], arguments["name"]]
        if arguments.get("namespace"):
            args.extend(["-n", arguments["namespace"]])
        result = run_kubectl(args, timeout=60)

    elif name == "kubectl_logs":
        args = ["logs", arguments["pod"], "-n", arguments["namespace"]]

        if arguments.get("container"):
            args.extend(["-c", arguments["container"]])

        args.extend(["--tail", str(arguments.get("tail", 100))])

        if arguments.get("previous"):
            args.append("--previous")

        if arguments.get("since"):
            args.extend(["--since", arguments["since"]])

        result = run_kubectl(args, timeout=60)

    elif name == "kubectl_events":
        args = ["get", "events", "-o", "json", "--sort-by=.lastTimestamp"]

        if arguments.get("namespace"):
            args.extend(["-n", arguments["namespace"]])
        else:
            args.append("-A")

        if arguments.get("for_resource"):
            args.extend(["--field-selector", f"involvedObject.name={arguments['for_resource']}"])

        result = run_kubectl(args)
        if result["success"] and result.get("stdout"):
            parsed = parse_json_output(result["stdout"])
            if parsed and "items" in parsed:
                events = []
                type_filter = arguments.get("types")
                for event in parsed["items"][-50:]:  # Last 50 events
                    event_type = event.get("type", "")
                    if type_filter and event_type != type_filter:
                        continue
                    events.append({
                        "type": event_type,
                        "reason": event.get("reason"),
                        "message": event.get("message"),
                        "object": f"{event.get('involvedObject', {}).get('kind')}/{event.get('involvedObject', {}).get('name')}",
                        "namespace": event.get("metadata", {}).get("namespace"),
                        "count": event.get("count", 1),
                        "lastTimestamp": event.get("lastTimestamp"),
                    })
                result["events"] = events
                result["count"] = len(events)

    elif name == "kubectl_top":
        args = ["top", arguments["resource"]]

        if arguments["resource"] == "pods":
            if arguments.get("namespace"):
                args.extend(["-n", arguments["namespace"]])
            else:
                args.append("-A")

        if arguments.get("selector"):
            args.extend(["-l", arguments["selector"]])

        result = run_kubectl(args, timeout=30)

    elif name == "kubectl_api_resources":
        args = ["api-resources", "-o", "wide"]

        if arguments.get("api_group"):
            args.extend(["--api-group", arguments["api_group"]])

        if arguments.get("namespaced") is True:
            args.append("--namespaced=true")
        elif arguments.get("namespaced") is False:
            args.append("--namespaced=false")

        result = run_kubectl(args)

    elif name == "kubectl_get_contexts":
        result = run_kubectl(["config", "get-contexts"])
        current = run_kubectl(["config", "current-context"])
        if current["success"]:
            result["current_context"] = current["stdout"].strip()

    elif name == "kubectl_cluster_info":
        result = run_kubectl(["cluster-info"])

    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
