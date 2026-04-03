import accelforge as af


spec = af.Spec.from_yaml(
    af.examples.arches.simple,
    af.examples.workloads.matmuls,
    af.examples.mappings.unfused_matmuls_to_simple,
    jinja_parse_data={
        "N_EINSUMS": 2,
        "M": 64,
        "KN": 32,
        "MainMemoryEnergy": 10,
        "GlobalBufferSize": 1e5
    }
)

print(spec.arch)
print(spec.mapping)
print(spec.workload)
