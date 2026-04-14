def grid(einsums: list[str], units: list[str], einsum_path, arch_path):
    """
    [einsum_path] and [arch_path] are functions which take an einsum 
    or arch name respectively, and return the path to the appropriate 
    .yaml file.
    """
    grid = {}
    for sub_arch in units:
        for einsum in einsums:
            grid[(sub_arch, einsum)] = map(
                arch_path(sub_arch),
                einsum_path(einsum)
            )
    return grid
