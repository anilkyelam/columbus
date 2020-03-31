import matplotlib.pyplot as plt
import math
import numpy as np

results = []
input_file = "/home/anil/Desktop/benchmarking/memory/results17.out"
with open(input_file, "r") as fp:
    for line in fp:
        float_list = [float(i) for i in line.split()]
        results.append(float_list)
# print(results)

if results[0].__len__() == 2:

    sizes = sorted(set(map(lambda r: r[0], results)))
    values_in_ns = []
    for size in sizes:
        size_filtered = list(map(lambda l: l[1], filter(lambda r: r[0] == size, results)))
        values_in_ns.append(np.median(size_filtered)/2.7)

    log_sizes = list(map(lambda r: math.log(r, 2), sizes))

    plt.xlabel('Log2 (Array size - number of integers)')
    plt.ylabel('Latency in ns')
    plt.title('Memory access latency')
    plt.plot(log_sizes, values_in_ns, color="black")
    plt.show()
