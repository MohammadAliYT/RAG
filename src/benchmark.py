import resource
from time import perf_counter

from fastembed import TextEmbedding

# Measure how long model initialization takes
start = perf_counter()

model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

print(f"Model initialization: {perf_counter() - start:.3f}s")

question = "Why can an American call option be exercised early?"

# Run the same question three times
for run in range(1, 4):
    start = perf_counter()

    embedding = list(model.embed([question]))[0]

    duration = (perf_counter() - start) * 1000

    print(f"Run {run}: {duration:.2f} ms")
    print(f"Vector dimensions: {len(embedding)}")

# On macOS, ru_maxrss is reported in bytes
peak_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024

print(f"Peak process memory: {peak_memory:.1f} MB")
