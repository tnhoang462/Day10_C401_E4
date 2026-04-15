import chromadb, os
from sentence_transformers import SentenceTransformer

# Handle path variations depending on where the script is run from
docs_dir = './data/docs'
if not os.path.exists(docs_dir):
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'docs')

client = chromadb.PersistentClient(path='./chroma_db')
col = client.get_or_create_collection('day09_docs')
model = SentenceTransformer('all-MiniLM-L6-v2')

for fname in os.listdir(docs_dir):
    with open(os.path.join(docs_dir, fname), encoding='utf-8') as f:
        content = f.read()
    
    # Chunking the content into paragraphs
    paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
    
    if not paragraphs: continue
    
    embeddings = model.encode(paragraphs).tolist()
    ids = [f"{fname}_{i}" for i in range(len(paragraphs))]
    metadatas = [{"source": fname} for _ in paragraphs]
    
    col.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=paragraphs,
        metadatas=metadatas
    )
    print(f'Indexed {len(paragraphs)} chunks from: {fname}')

print('Index ready. (Total docs: {})'.format(col.count()))
