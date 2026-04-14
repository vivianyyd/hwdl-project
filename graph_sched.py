import re
import numpy as np
import matplotlib.pyplot as plt

# -------- INPUT --------
data_str = """
{
(E0, compute=fast, latency=0.0001841295452322811): 0, 
(E2, compute=fast, latency=0.0001841295452322811): np.float32(0.00018412955), 
(E1, compute=slow, latency=2.080000012938399e-05): 0, 
(E3, compute=slow, latency=2.080000012938399e-05): np.float32(0.00018412955), 
(E4, compute=slow, latency=2.080000012938399e-05): np.float32(0.0003682591)
}
"""

# -------- PARSE --------
pattern = re.compile(
    r"\((E\d+), compute=(\w+), latency=([0-9e\.\-]+)\): (.+?)(?:,|\n|\})"
)

events = []

for match in pattern.findall(data_str):
    eid, compute, latency, start = match

    latency = float(latency)

    if "np.float32" in start:
        start = float(re.findall(r"np\.float32\((.*?)\)", start)[0])
    else:
        start = float(start)

    end = start + latency

    events.append({
        "id": eid,
        "compute": compute,
        "start": start * 1000,
        "end": end * 1000
    })

# -------- PLOT --------
fig, ax = plt.subplots(figsize=(6, 8))

unit_index = {"fast": 0, "slow": 1}

for e in events:
    x = unit_index[e["compute"]]
    y = e["start"]
    height = e["end"] - e["start"]

    color = "red" if e["compute"] == "fast" else "blue"

    # Draw block
    rect = ax.bar(
        x,
        height,
        bottom=y,
        width=0.6,
        color=color,
        edgecolor="black"
    )

    # Add label (einsum id)
    ax.text(
        x,
        y + height / 2,
        e["id"],
        ha="center",
        va="center",
        fontsize=10,
        color="white",
        fontweight="bold"
    )

# -------- FORMATTING --------
ax.set_xticks([0, 1])
ax.set_xticklabels(["fast", "slow"])
ax.set_ylabel("Time (ms)")
ax.set_title("Generated Schedule")

# Optional: invert so time flows downward
ax.invert_yaxis()

plt.tight_layout()
plt.savefig("milestone_2.png", dpi=300)
