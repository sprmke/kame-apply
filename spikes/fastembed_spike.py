import time, random, psutil, os
from fastembed import TextEmbedding
random.seed(1)
words = "senior python developer remote fastapi postgres aws kubernetes team lead data engineer react vue nuxt product manager design agile scrum sql cloud devops ml model pipeline api microservices testing ci cd security observability terraform docker".split()
texts = [" ".join(random.choices(words, k=180)) for _ in range(1000)]  # ~ job description sized
p = psutil.Process(os.getpid())
t=time.time(); m = TextEmbedding("BAAI/bge-small-en-v1.5"); load=time.time()-t
t=time.time(); vecs=list(m.embed(texts, batch_size=32)); dt=time.time()-t
print(f"model load {load:.1f}s | 1000 texts {dt:.1f}s ({1000/dt:.0f}/s) | dim {len(vecs[0])} | rss {p.memory_info().rss/1e6:.0f} MB")
