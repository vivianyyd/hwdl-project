import re
import numpy as np
import matplotlib.pyplot as plt

# -------- INPUT --------
data_str = """
{(EF, compute=fast, latency=0.0001841295452322811): 0,
 (AB, compute=fast, latency=0.0001841295452322811): 0.0001841295452322811,
 (CD, compute=slow, latency=0.0008597790728103675): 0,
 (GH, compute=fast, latency=0.0001841295452322811): 0.0003682590904645622,
 (EFGH, compute=fast, latency=0.0001841295452322811): 0.0005523886356968433,
 (ABCD, compute=fast, latency=0.0001841295452322811): 0.0008597790728103675,
 (OUT, compute=fast, latency=0.0001841295452322811): 0.0010439086180426486}
"""

# -------- PARSE --------
pattern = re.compile(
    r"\((\w+), compute=(\w+), latency=([0-9e\.\-]+)\): (.+?)(?:,|\n|\})"
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
plt.savefig("milestone_3.png", dpi=300)
