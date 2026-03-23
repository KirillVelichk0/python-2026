import numpy as np
import time
import multiprocessing as mp

def gelu(x):
    return 0.5 * x * (1 + np.tanh(np.sqrt(2/np.pi)*(x + 0.044715*x**3)))

def gelu_chunk(chunk):
    return gelu(chunk)

if __name__ == "__main__":
    N = mp.cpu_count()
    total_points = 10000 * N
    data = np.random.randn(total_points).astype(np.float32)

    # Последовательный расчёт (1 ядро)
    start = time.time()
    result_seq = gelu(data)
    end = time.time()
    print(f"Time on 1 core: {end - start:.4f} s")

    # Параллельный расчёт (N ядер)
    start = time.time()
    chunks = np.array_split(data, N)
    with mp.Pool(N) as pool:
        result_par = pool.map(gelu_chunk, chunks)
    result_par = np.concatenate(result_par)
    end = time.time()
    print(f"Time on {N} cores: {end - start:.4f} s")

    # Проверка корректности
    print("Max difference:", np.max(np.abs(result_seq - result_par)))
