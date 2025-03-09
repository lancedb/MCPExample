from pathlib import Path

def get_project_slug(codebase_path: str) -> str:
    """Generate a unique project slug based on the path"""
    #path_hash = hashlib.md5(codebase_path.encode()).hexdigest()[:8]
    base_name = Path(codebase_path).name
    #return f"{base_name}_{path_hash}"
    return base_name


def get_central_storage_dir() -> Path:
    """Get the central storage directory for all project artifacts"""
    home_dir = Path.home()
    storage_dir = home_dir / ".basicmcp" / "codeqa_indices"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir

def list_codebases():
    codebases = get_central_storage_dir()
    # Get list of folders in storage directory
    storage_path = codebases
    if not storage_path.exists():
        return "No codebases found."
        
    folders = [folder.name for folder in storage_path.iterdir() if folder.is_dir()]

    return folders