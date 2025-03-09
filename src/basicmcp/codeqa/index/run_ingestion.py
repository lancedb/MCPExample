# ... existing imports ...
import hashlib
from pathlib import Path
from typing import Tuple
import shutil
import sys
import logging

# Add logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from basicmcp.codeqa.index.preprocess import (
    load_files,
    parse_code_files,
    find_references,
    write_class_data_to_csv,
    write_method_data_to_csv,
)
from basicmcp.codeqa.index.ingest import (
    Method, Class, clip_text_to_max_tokens, MAX_TOKENS,
    get_name_and_input_dir, process_special_files, get_special_files,
    create_markdown_dataframe, ingest_to_database
)
from basicmcp.codeqa.util import get_central_storage_dir, get_project_slug
import tempfile
import git
from urllib.parse import urlparse


def run_ingestion(codebase_path: str) -> Tuple[str, Path]:
    """
    Run the ingestion process programmatically
    Args:
        codebase_path: Path to local codebase or GitHub repository URL
    Returns:
        tuple: (project_slug, artifacts_dir)
    """
    # Handle GitHub repository URLs
    if codebase_path.startswith(('http://', 'https://')):
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                logger.info(f"Cloning repository: {codebase_path}")
                repo_path = Path(tmp_dir) / urlparse(codebase_path).path.split('/')[-1]
                git.Repo.clone_from(codebase_path, repo_path)
                return _run_ingestion(str(repo_path))
        except git.GitCommandError as e:
            logger.error(f"Failed to clone repository: {e}")
            raise
    else:
        return _run_ingestion(codebase_path)

def _run_ingestion(codebase_path: str) -> Tuple[str, Path]:
    """Internal function to handle the actual ingestion process"""
    project_slug = get_project_slug(codebase_path)
    central_dir = get_central_storage_dir()
    artifacts_dir = central_dir / project_slug
    
    # Create fresh artifacts directory
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
    artifacts_dir.mkdir(parents=True)

    # Process code files
    files = load_files(codebase_path)
    class_data, method_data, class_names, method_names = parse_code_files(files)
    references = find_references(files, class_names, method_names)

    # Map references
    class_data_dict = {cd['class_name']: cd for cd in class_data}
    method_data_dict = {(md['class_name'], md['name']): md for md in method_data}

    for class_name, refs in references['class'].items():
        if class_name in class_data_dict:
            class_data_dict[class_name]['references'] = refs

    for method_name, refs in references['method'].items():
        for key in method_data_dict:
            if key[1] == method_name:
                method_data_dict[key]['references'] = refs

    # Convert back to lists
    class_data = list(class_data_dict.values())
    method_data = list(method_data_dict.values())

    # Process special files
    special_files = get_special_files(codebase_path)
    special_contents = process_special_files(special_files)

    # Write to central storage
    write_class_data_to_csv(class_data, artifacts_dir)
    write_method_data_to_csv(method_data, artifacts_dir)

    # Ingest data into database
    ingest_to_database(artifacts_dir, project_slug, method_data, class_data, special_contents)

    return project_slug, artifacts_dir


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Please provide the codebase path as an argument.")
        sys.exit(1)
    project_slug, artifacts_dir = run_ingestion(sys.argv[1])
    logger.info("Processing complete. Artifacts stored in: %s", artifacts_dir)