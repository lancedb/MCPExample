import os
import sys
import pandas as pd
import lancedb
import logging
from pathlib import Path
from lancedb.embeddings import EmbeddingFunctionRegistry
from lancedb.pydantic import LanceModel, Vector
import tiktoken
from dotenv import load_dotenv
from basicmcp.codeqa.util import get_central_storage_dir

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_name_and_input_dir(codebase_path):
    codebase_folder_name = Path(codebase_path).name
    storage_dir = get_central_storage_dir()
    
    logger.info("codebase_folder_name: %s", codebase_folder_name)
    
    output_directory = storage_dir / codebase_folder_name
    os.makedirs(output_directory, exist_ok=True)
    
    return codebase_folder_name, output_directory

def get_special_files(directory):
    md_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.md', '.sh')):
                full_path = os.path.join(root, file)
                md_files.append(full_path)
    return md_files

def process_special_files(md_files):
    contents = {}
    for file_path in md_files:
        with open(file_path, 'r', encoding='utf-8') as file:
            contents[file_path] = file.read()  # Store the content against the file path
    return contents


def create_markdown_dataframe(markdown_contents):
    # Create a DataFrame from markdown_contents dictionary
    df = pd.DataFrame(list(markdown_contents.items()), columns=['file_path', 'source_code'])
    
    # Format the source_code with file information and apply clipping
    df['source_code'] = df.apply(lambda row: f"File: {row['file_path']}\n\nContent:\n{clip_text_to_max_tokens(row['source_code'], MAX_TOKENS)}\n\n", axis=1)
    
    # Add placeholder "empty" for the other necessary columns
    for col in ['class_name', 'constructor_declaration', 'method_declarations', 'references']:
        df[col] = "empty"
    return df


# Check for environment variables and select embedding model
#if os.getenv("JINA_API_KEY"):
#    logger.info("Using Jina")
#    MODEL_NAME = "jina-embeddings-v3"
#    registry = EmbeddingFunctionRegistry.get_instance()
#    model = registry.get("jina").create(name=MODEL_NAME, max_retries=2)
#    EMBEDDING_DIM = 1024  # Jina's dimension
#    MAX_TOKENS = 4000   # Jina uses a different tokenizer so it's hard to predict the number of tokens
#else:
#    logger.info("Using OpenAI")
#    #MODEL_NAME = "text-embedding-3-large"
#    registry = EmbeddingFunctionRegistry.get_instance()
#    #model = registry.get("openai").create(name=MODEL_NAME, max_retries=2, api_key="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")
#    #EMBEDDING_DIM = model.ndims()  # OpenAI's dimension
#
#    MODEL_NAME = "BAAI/bge-small-en-v1.5" #"BAAI/bge-m3"
#    model = registry.get("sentence-transformers").create(name=MODEL_NAME)
#    EMBEDDING_DIM = model.ndims()
#    MAX_TOKENS = 8000    # OpenAI's token limit

MAX_TOKENS = 8000
MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = None
model = None
registry = EmbeddingFunctionRegistry.get_instance()

def init_model():
    global model
    global EMBEDDING_DIM
    if model is None:
        model = registry.get("sentence-transformers").create(name=MODEL_NAME)
        EMBEDDING_DIM = model.ndims()
    return model

init_model()

class Method(LanceModel):
    code: str = model.SourceField()
    method_embeddings: Vector(EMBEDDING_DIM) = model.VectorField()
    file_path: str
    class_name: str
    name: str
    doc_comment: str
    source_code: str
    references: str

class Class(LanceModel):
    source_code: str = model.SourceField()
    class_embeddings: Vector(EMBEDDING_DIM) = model.VectorField()
    file_path: str
    class_name: str
    constructor_declaration: str
    method_declarations: str
    references: str

def clip_text_to_max_tokens(text, max_tokens, encoding_name='cl100k_base'):
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)
    original_token_count = len(tokens)
    
    logger.debug("\nOriginal text (%d tokens):", original_token_count)
    logger.debug("=" * 50)
    logger.debug(text[:200] + "..." if len(text) > 200 else text)
    
    if original_token_count > max_tokens:
        tokens = tokens[:max_tokens]
        clipped_text = encoding.decode(tokens)
        logger.debug("\nClipped text (%d tokens):", len(tokens))
        logger.debug("=" * 50)
        logger.debug(clipped_text[:200] + "..." if len(clipped_text) > 200 else clipped_text)
        return clipped_text
    
    return text

def ingest_to_database(uri: str, table_name: str, method_data: list, class_data: list, special_contents: dict = None):
    db = lancedb.connect(uri)

    try:
        # Create and populate method table
        table = db.create_table(
            table_name + "_method", 
            schema=Method, 
            mode="overwrite",
            on_bad_vectors='drop'
        )

        method_df = pd.DataFrame(method_data)
        method_df['code'] = method_df['source_code']
        method_df = method_df.fillna('empty')
        logger.info("Adding method data to table")
        table.add(method_df)
    
        # Create and populate class table
        class_table = db.create_table(
            table_name + "_class", 
            schema=Class, 
            mode="overwrite",
            on_bad_vectors='drop'
        )
        # Convert list to DataFrame
        class_df = pd.DataFrame(class_data)
        class_df = class_df.fillna('empty')

        class_df['source_code'] = class_df.apply(
            lambda row: "File: " + row['file_path'] + "\n\n" +
                    "Class: " + row['class_name'] + "\n\n" +
                    "Source Code:\n" + 
                    clip_text_to_max_tokens(row['source_code'], MAX_TOKENS) + "\n\n",
            axis=1
        )

        if len(class_data) == 0:
            columns = ['source_code', 'file_path', 'class_name', 'constructor_declaration', 
                      'method_declarations', 'references']
            class_data = pd.DataFrame({col: ["empty"] for col in columns})
            
        logger.info("Adding class data to table")
        class_table.add(class_data)

        if special_contents and len(special_contents) > 0:
            markdown_df = create_markdown_dataframe(special_contents)
            logger.info("Adding %d special files to table", len(markdown_df))
            class_table.add(markdown_df)

        logger.info("Data ingestion completed successfully")

    except Exception as e:
        logger.error("Error during ingestion: %s", str(e))
        if f"{table_name}_method" in db:
            db.drop_table(f"{table_name}_method")
        if f"{table_name}_class" in db:
            db.drop_table(f"{table_name}_class")
        raise e

if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("Usage: python script.py <code_base_path>")
        sys.exit(1)

    codebase_path = sys.argv[1]

    table_name, input_directory = get_name_and_input_dir(codebase_path)
    method_data_file = os.path.join(input_directory, "method_data.csv")
    class_data_file = os.path.join(input_directory, "class_data.csv")

    special_files = get_special_files(codebase_path)
    special_contents = process_special_files(special_files)

    method_data = pd.read_csv(method_data_file)
    class_data = pd.read_csv(class_data_file)

    logger.info(class_data.head())

    ingest_to_database(table_name, method_data, class_data, special_contents)