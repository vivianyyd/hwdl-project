import accelforge as af

spec = af.Spec.from_yaml(
    "arch.yaml",
    "workload.yaml",
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

result = spec.map_workload_to_arch()
with open("image.svg", "w") as f:
    f.write(result.render())
