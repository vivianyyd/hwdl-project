import accelforge as af

spec = af.Spec.from_yaml(
    "eyeriss.yaml",
    "flop.yaml",
    jinja_parse_data={
        "N_EINSUMS": 2,
        "M": 64,
        "KN": 32,
        "MainMemoryEnergy": 10,
        "GlobalBufferSize": 1e5
    }
)

# print(spec.arch)
# print(spec.workload)
# print(spec.mapper.metrics)
spec.mapper.metrics = af.Metrics.LATENCY | af.Metrics.ENERGY

# result = spec.map_workload_to_arch()
with open("image.svg", "w") as f:
    f.write(spec.arch.render())

# actions = 0

# einsum = "Matmul1"
# for tensor in ["T0", "X", "C"]:
#     actions += (result.data[einsum+"<SEP>action<SEP>MainMemory<SEP>"+tensor+"<SEP>read"]).iloc[0]
#     actions += (result.data[einsum+"<SEP>action<SEP>MainMemory<SEP>"+tensor+"<SEP>write"]).iloc[0]

# einsum = "Vec"
# for tensor in ["T1", "Y", "T2"]:
#     actions += (result.data[einsum+"<SEP>action<SEP>MainMemory<SEP>"+tensor+"<SEP>read"]).iloc[0]
#     actions += (result.data[einsum+"<SEP>action<SEP>MainMemory<SEP>"+tensor+"<SEP>write"]).iloc[0]

# einsum = "Add"
# for tensor in ["C", "T2", "T3"]:
#     actions += (result.data[einsum+"<SEP>action<SEP>MainMemory<SEP>"+tensor+"<SEP>read"]).iloc[0]
#     actions += (result.data[einsum+"<SEP>action<SEP>MainMemory<SEP>"+tensor+"<SEP>write"]).iloc[0]

# print(actions)
# # print(result.data["Total<SEP>energy"])
# # print(result.data.columns)

# print(result.latency(per_einsum=True))
# latency = result.latency()

# print(actions / latency)
# total_reads = 0
# total_writes = 0
# for (einsum, lat) in latency.items():
#     component = "MainMemory"
#     reads = actions[(einsum, component, "read")]
#     writes = actions[(einsum, component, "write")]
#     print((reads + writes) / lat)
#     total_reads += reads
#     total_writes += writes
# print(result.latency())
# print((total_reads + total_writes) /result.latency())


# r/w then latencies per einsum:

# 1x1 fanout:
# 529408.0
# {'Matmul1': 8.17600000000000e-5, 'Vec': 4.80000000000000e-7, 'Add': 4.80000000000000e-7}

#8x4 fanout:
# 325632.0
# {'Matmul1': 4.99200000000000e-5, 'Vec': 4.80000000000000e-7, 'Add': 4.80000000000000e-7}

# 14x12
#522240.0
#{'Matmul1': 8.06400000000000e-5, 'Vec': 4.80000000000000e-7, 'Add': 4.80000000000000e-7}

# 32x8
#284672.0
#{'Matmul1': 4.35200000000000e-5, 'Vec': 4.80000000000000e-7, 'Add': 4.80000000000000e-7}

# 8x32
# 272384.0
# {'Matmul1': 4.16000000000000e-5, 'Vec': 4.80000000000000e-7, 'Add': 4.80000000000000e-7}

#128x128
# 269312.0
# {'Matmul1': 4.11200000000000e-5, 'Vec': 4.80000000000000e-7, 'Add': 4.80000000000000e-7}