from dotenv import load_dotenv
load_dotenv()
import os
import re
import lancedb
import logging
from openai import OpenAI
from lancedb.rerankers import AnswerdotaiRerankers
from .prompt import HYDE_SYSTEM_PROMPT, HYDE_V2_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
from basicmcp.codeqa.index.ingest import get_name_and_input_dir
from basicmcp.codeqa.util import get_project_slug, get_central_storage_dir

# Database setup
def setup_database(codebase_path):
    codebase_folder_name, output_path = get_name_and_input_dir(codebase_path)
    
    db = lancedb.connect(output_path)
    tables = [ codebase_folder_name + "_method", codebase_folder_name + "_class"]
    if not all(table in db.table_names() for table in tables):
        raise ValueError(f"Tables {tables} not found in the database. Please index the codebase first")

    method_table = db.open_table(codebase_folder_name + "_method")
    class_table = db.open_table(codebase_folder_name + "_class")

    return method_table, class_table

# OpenAI client setup
OAI_CLIENT = None

# reranker
RERANKER = None

def check_and_init_openai():
    if os.environ.get('OPENAI_API_KEY'):
        global OAI_CLIENT
        if OAI_CLIENT is None:
            OAI_CLIENT = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        return OAI_CLIENT
    else:
        logging.info("OPENAI_API_KEY not found in environment variables")

# Replace groq_hyde function
def openai_hyde(query):
    chat_completion = OAI_CLIENT.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": HYDE_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"Help predict the answer to the query: {query}",
            }
        ]
    )
    return chat_completion.choices[0].message.content

def openai_hyde_v2(query, temp_context, hyde_query):
    chat_completion = OAI_CLIENT.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": HYDE_V2_SYSTEM_PROMPT.format(query=query, temp_context=temp_context)
            },
            {
                "role": "user",
                "content": f"Predict the answer to the query: {hyde_query}",
            }
        ]
    )
    return chat_completion.choices[0].message.content


def openai_chat(query, context):
    chat_completion = OAI_CLIENT.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": CHAT_SYSTEM_PROMPT.format(context=context)
            },
            {
                "role": "user",
                "content": query,
            }
        ]
    )
    return chat_completion.choices[0].message.content

def process_input(input_text):
    processed_text = input_text.replace('\n', ' ').replace('\t', ' ')
    processed_text = re.sub(r'\s+', ' ', processed_text)
    processed_text = processed_text.strip()
    
    return processed_text

def generate_context(codebase_path, query, rerank=True):
    try:
        check_and_init_openai()
        method_table, class_table = setup_database(codebase_path)
        #hyde_query = openai_hyde(query) if OAI_CLIENT is not None else query
        hyde_query = query
        method_docs = method_table.search(hyde_query, query_type="hybrid")
        class_docs = class_table.search(hyde_query, query_type="hybrid")

        #temp_context = '\n'.join(method_docs['code'].tolist() + class_docs['source_code'].tolist())
        #if OAI_CLIENT:
        #    hyde_query_v2 = openai_hyde_v2(query, temp_context, hyde_query)

        #    logging.info("-query_v2-")
        #    logging.info(hyde_query_v2)
        #    method_search = method_table.search(hyde_query_v2)
        #    class_search = class_table.search(hyde_query_v2)

        if rerank:
            global RERANKER
            if RERANKER is None:
                RERANKER = AnswerdotaiRerankers(column="source_code")
            method_docs = method_docs.rerank(RERANKER)
            class_docs = class_docs.rerank(RERANKER)

        method_docs = method_docs.limit(5).to_pandas()
        class_docs = class_docs.limit(5).to_pandas()

        top_3_methods = method_docs.to_dict('records')[:3]
        methods_combined = "\n\n".join(f"File: {doc['file_path']}\nCode:\n{doc['code']}" 
                                     for doc in top_3_methods)

        top_3_classes = class_docs.to_dict('records')[:3]
        classes_combined = "\n\n".join(f"File: {doc['file_path']}\nClass Info:\n{doc['source_code']} "
                                     f"References: \n{doc.get('references', '')}  \n END OF ROW {i}" 
                                     for i, doc in enumerate(top_3_classes))

        return methods_combined + "\n below is class or constructor related code \n" + classes_combined

    except Exception as e:
        logging.error("Error in generate_context: %s", str(e))
        return f"Error generating context: {str(e)}"

