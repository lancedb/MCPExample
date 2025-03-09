import lancedb
import pyarrow as pa
import numpy as np

# Connect to a database (or create if it doesn't exist)
db = lancedb.connect("./multi_vector_list_example.db")

# Create a table with multi-vector data where each vector is a list of embeddings
def create_multi_vector_list_table():
    # Generate 5 rows of data, where each row has a nested vector structure
    num_rows = 5
    
    # Create vector data where each vector is a list of 2 sub-vectors
    # Each sub-vector is a 2-dimensional vector
    vector_data = [
        [[i, i + 1], [i + 2, i + 3]] for i in range(num_rows)
    ]
    
    id_data = list(range(1, num_rows + 1))
    text_data = [f"Sample text {i}" for i in range(num_rows)]
    
    # Create the Arrow table with proper schema
    # Note the nested list type: list(list(float32))
    df = pa.table(
        {
            "id": pa.array(id_data),
            "text": pa.array(text_data),
            "vector": pa.array(
                vector_data, 
                type=pa.list_(pa.list_(pa.float32(), list_size=2))
            ),
        }
    )
    
    # Create the table
    return db.create_table("multi_vector_list", df, mode="overwrite")

# Create the table
table = create_multi_vector_list_table()
print("Created table with schema:")
print(table.schema)

# Example 1: Query with a multi-vector list
# Create a query vector that matches the structure of the data vectors
query_vector = [[1.0, 2.0], [3.0, 4.0]]

# Search using the nested vector structure
results = table.search(query_vector).limit(3).to_pandas()
print("\nSearch results using multi-vector list:")
print(results[["id", "text", "_distance"]])

# Example 2: Create index on the multi-vector column
# Note: For multi-vector lists, you need to specify the exact vector structure
# when creating the index
#table.create_index(
#    vector_column_name="vector",
#    index_type="IVF_PQ",  # Index type
#    metric="cosine"       # Distance metric
#)

print("\nCreated index on the multi-vector column")

# Search again with the index
results_with_index = table.search(query_vector).limit(3).to_pandas()
print("\nSearch results using multi-vector list with index:")
print(results_with_index[["id", "text", "_distance"]])

