import lancedb
import logging
import base64
import re
import mcp
from pathlib import Path
from io import BytesIO
from PIL import Image
from typing import Optional, Union, List, Tuple
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry

## TODO: switch to cloud and figure out simple ways to allow users to provide cloud auth
LOCAL_STORAGE_DIR = Path.home() / ".basicmcp" 
TBL_NAME = "globalDB"
MODEL = None

def get_global_table():
    model = get_registry().get("open-clip").create(max_retries=0) if MODEL is None else MODEL

    class Schema(LanceModel):
        text: str = model.SourceField()
        img: bytes = model.SourceField()
        vector_img: Vector(model.ndims()) = model.VectorField()
        vector_txt: Vector(model.ndims()) = model.VectorField()
    
    db = lancedb.connect(LOCAL_STORAGE_DIR)
    if "globalDB" in db:
        return db["globalDB"]
    else:
        try:
            return db.create_table("globalDB", schema=Schema)
        except Exception as e:
            import pdb; pdb.set_trace()
            return f"Error: {e}"

def pil_to_bytes(pil_image, format="PNG"):
    """
    Convert a PIL Image to bytes.
    
    Args:
        pil_image: PIL Image object
        format: Image format (PNG, JPEG, etc.)
        
    Returns:
        Image as bytes
    """
    img_byte_arr = BytesIO()
    pil_image.save(img_byte_arr, format=format)
    img_byte_arr.seek(0)  # Move to the beginning of BytesIO object
    return img_byte_arr.getvalue()

def is_base64_image(string):
    # Check if the string matches base64 pattern
    pattern = r'^[A-Za-z0-9+/]+={0,2}$'
    
    # If the string starts with a data URL prefix, remove it
    if string.startswith('data:image'):
        # Extract the base64 part
        try:
            string = string.split(',')[1]
        except IndexError:
            return False
    
    # Check if string matches base64 pattern
    if not re.match(pattern, string):
        return False
        # Try to decode the string
    try:
        image_data = base64.b64decode(string)
        # Try to open it as an image
        img = Image.open(BytesIO(image_data))
        img.verify()  # Verify it's an image
        return True
    except Exception:
        return False
    
    return True
def create_empty_image(size=(1, 1), color='white'):
    """
    Create an empty PIL Image.
    
    Args:
        size: Tuple of (width, height)
        color: Background color
        
    Returns:
        PIL Image object
    """
    return Image.new('RGB', size, color)

def ingest_data(texts: Optional[List[str]] = None, imgs: Optional[List[Union[bytes, Image.Image, str]]] = None):
    if imgs is None and texts is None:
        raise ValueError("Either text or img must be provided")
    
    if imgs is None:
        empty_img = create_empty_image()
        imgs = [pil_to_bytes(empty_img)] * len(texts)
    elif isinstance(imgs[0], Image.Image):
        imgs = [pil_to_bytes(img) for img in imgs]
    elif is_base64_image(imgs[0]):
        logging.info("Decoding base64 image")
        imgs = [base64.b64decode(img) for img in imgs]
    elif isinstance(imgs[0], str):
        imgs = [pil_to_bytes(Image.open(img)) for img in imgs]

    if texts is None:
        texts = [""] * len(imgs)
        
    try:
        table = get_global_table()
        table.add([
            {
                "text": text,
                "img": img,
        
            }
            for text, img in zip(texts, imgs)
        ])
    except Exception as e:
        return f"Error: {e}"
    
    return f"Data ingested successfully! total length of table is {len(table)}"
    
def query_db(text: Optional[str] = None, img: Optional[Image] = None) -> Tuple[ List[Image], List[str] ]:
    if img is None and text is None:
        raise ValueError("Either text or img must be provided")

    query = text or img
    vector_column_name = "vector_txt" if text else "vector_img"
    table = get_global_table()
    rs = table.search(query, vector_column_name=vector_column_name, query_type="vector").limit(10).to_df()

    images = rs["img"].tolist()
    texts = rs["text"].tolist()
    images = [Image.open(BytesIO(img)) for img in images if img != b""]
    texts = [txt for txt in texts if txt!= ""]
    
    return images, texts


