# optional: sentence-transformers + faiss
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from .models import Memory

MODEL = SentenceTransformer("all-MiniLM-L6-v2")
DIM = 384
_index = None
_id_to_mem = {}

def init_index():
    global _index
    _index = faiss.IndexFlatL2(DIM)

def add_memory_to_index(mem: Memory):
    global _index, _id_to_mem
    vec = MODEL.encode([mem.content])[0].astype("float32")
    _index.add(np.expand_dims(vec, axis=0))
    _id_to_mem[_index.ntotal - 1] = str(mem.id)

def search_similar(query: str, top_k=5):
    vec = MODEL.encode([query]).astype("float32")
    D, I = _index.search(np.array(vec), top_k)
    ids = [ _id_to_mem.get(i) for i in I[0] if i in _id_to_mem ]
    return ids
