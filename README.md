# BasicMCP: A Code QA and Global Database MCP Server

> Built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction), this server provides intelligent code querying and global database management capabilities.

## Features

### Code QA System
- **Code Ingestion**: Support for both local codebases and GitHub repositories
- **Intelligent Querying**: Search and analyze code using semantic understanding
- **Multi-Format Support**: Handles various code file formats and structures
- **Reference Tracking**: Maintains relationships between classes and methods

### Global Database
- **Multi-Modal Storage**: Store and retrieve both text and images
- **Vector Search**: Semantic search capabilities using LanceDB
- **Base64 Support**: Handle base64 encoded images

## Tools

The server provides the following MCP tools:

### Code QA Tools
- `ingest_codebase`: Add a new codebase to the vector database
  - Supports local paths and GitHub repository URLs
  - Automatically processes and indexes code structure

- `codeqa`: Query and analyze ingested codebases
  - Natural language queries about code
  - Returns relevant code snippets and context

- `list_codebases`: List all available ingested codebases

### Global Database Tools
- `globaldb_ingest`: Store text and images in the global database
- `globaldb_query`: Query stored data using semantic search

## Installation

```bash
pip install basicmcp
```
{
  "mcpServers": {
    "codeqa": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/project",
        "run",
        "--python",
        "3.12",
        "basicmcp-codeqa"
      ]
    }
  }
}

Location:

- MacOS: ~/Library/Application Support/Claude/claude_desktop_config.json
- Windows: %APPDATA%/Claude/claude_desktop_config.json

