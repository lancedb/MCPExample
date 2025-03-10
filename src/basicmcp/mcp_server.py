from mcp.server.fastmcp import FastMCP
from basicmcp.codeqa.index.run_ingestion import run_ingestion
from basicmcp.codeqa.util import list_codebases
from basicmcp.codeqa.chat.search import generate_context
from basicmcp.global_db.ops import ingest_data, query_db, pil_to_bytes
from typing import List, Tuple, Union, Optional
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

mcp = FastMCP("codeqa")

@mcp.tool()
async def ingest_codebase(dir: str="/Users/ayushchaurasia/Documents/trolo") -> str:
    """
    Add a new codebase to the vector database
    Args:
        dir: Local path to codebase or github link to public repo
    """
    try:
        content = run_ingestion(dir)
        return f"Added codebase: {content}"
    except Exception as e:
        logger.error("Error in add_codebase: %s", str(e))
        raise

@mcp.tool()
async def codeqa(codebase: str, query: str, rerank=True) -> str:
    """
    Talk with codebase
    Args:
        codebase: The codebase to query. Can be a name, github link, or local path
        query: The search query
    """
    try:        
        # Get available codebases
        available_codebases = list_codebases()
        
        # Extract codebase name/slug
        if codebase.startswith(('http://', 'https://')):
            # For GitHub URLs, use the repo name as slug
            codebase_name = codebase.rstrip('/').split('/')[-1]
        else:
            # For local paths or names, use the last part of the path
            codebase_name = Path(codebase).name
            
        # Check if codebase is already ingested
        if codebase_name not in available_codebases:
            available_msg = "\nAvailable codebases:\n" + "\n".join(available_codebases) if available_codebases else "\nNo codebases are currently ingested."
            return f"Codebase '{codebase_name}' not found. Please ingest it first using ingest_codebase.{available_msg}"
        
        context = generate_context(codebase, query, rerank=rerank)
        if not context:
            return "No relevant context found for the query."
        return context
        
    except Exception as e:
        logger.error("Error in codeqa: %s", str(e))
        return f"Error processing query: {str(e)}"

@mcp.tool()
async def list_codebases_mcp():
    """
    List all codebases
    """
    try:
        folders = list_codebases()
        if not folders:
            return "No codebases found."
            
        return f"Available codebases:\n" + "\n".join(folders)
    except Exception as e:
        logger.error("Error in list_codebases: %s", str(e))
        return f"Error listing codebases: {str(e)}"

@mcp.tool()
async def globaldb_ingest(texts: Optional[List[str]] = None, imgs: Optional[List[str]] = None):
    """
    Ingest data into the global database
    Args:
        texts: List of texts
        imgs: List of images
    """

    return ingest_data(texts, imgs)

@mcp.tool()
async def globaldb_query(query: str):
    """
    Query the global database
    Args:
        query: The search query
    """
    return query_db(query)


if __name__ == "__main__":
    try:
        context = run_ingestion("https://github.com/lancedb/lancedb")
        context = generate_context("lancedb", "what is lancedb")
        print(context)
    except Exception as e:
        logger.error("Error in main: %s", str(e))
