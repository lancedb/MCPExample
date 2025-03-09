from basicmcp.dummy.server import mcp


def main():
    """Main entry point for the package."""
    mcp.run()


__all__ = ["main"]

if __name__ == "__main__":
    main()