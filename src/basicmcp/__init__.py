from basicmcp.mcp_server import mcp


def main():
    """Main entry point for the package."""
    mcp.run(transport='stdio')


__all__ = ["main"]
