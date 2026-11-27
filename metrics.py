
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from config import RESULTS_DIR


RESULTS = Path(RESULTS_DIR)
RESULTS.mkdir(parents=True, exist_ok=True)


def save_graph(fig, filename):

    path = RESULTS / filename

    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)

    print("[GRAPH] Saved:", path)


def plot_delivery_rate():

    conditions = [
        "Normal conditions",
        "30% simulated loss"
    ]

    rates = [
        3 / 3 * 100,
        30 / 30 * 100
    ]

    fig, ax = plt.subplots(figsize=(8, 5))

    bars = ax.bar(
        conditions,
        rates,
        color=["#2563eb", "#16a34a"]
    )

    ax.bar_label(bars, fmt="%.1f%%")

    ax.set_ylim(0, 115)
    ax.set_ylabel("Acknowledgment rate (%)")
    ax.set_title("Reliable UDP Delivery Rate")
    ax.grid(axis="y", alpha=0.3)

    save_graph(fig, "delivery_rate.png")


def plot_retransmissions():

    labels = [
        "Original packets",
        "Acknowledged",
        "Retransmissions",
        "Simulated drops",
        "Failed packets"
    ]

    values = [30, 30, 49, 33, 0]

    fig, ax = plt.subplots(figsize=(10, 5))

    bars = ax.bar(
        labels,
        values,
        color=[
            "#2563eb",
            "#16a34a",
            "#f59e0b",
            "#ef4444",
            "#64748b"
        ]
    )

    ax.bar_label(bars)
    ax.set_ylim(0, 60)
    ax.set_ylabel("Packet count")
    ax.set_title(
        "Reliable UDP Under 30% Simulated Loss"
    )

    ax.tick_params(axis="x", rotation=15)
    ax.grid(axis="y", alpha=0.3)

    save_graph(fig, "packet_loss_recovery.png")


def plot_file_performance():

    operations = [
        "Replication",
        "Normal download",
        "Owner offline download"
    ]

    times = [0.543, 2.032, 2.119]

    fig, ax = plt.subplots(figsize=(9, 5))

    bars = ax.bar(
        operations,
        times,
        color=[
            "#2563eb",
            "#16a34a",
            "#f59e0b"
        ]
    )

    ax.bar_label(bars, fmt="%.3f s")
    ax.set_ylim(0, 2.6)
    ax.set_ylabel("Time (seconds)")
    ax.set_title("File Operation Performance")
    ax.grid(axis="y", alpha=0.3)

    save_graph(fig, "file_performance.png")


def plot_chunk_distribution():

    distribution = [
        [1, 1, 1, 1],
        [1, 0, 1, 1],
        [1, 1, 0, 1],
        [0, 1, 1, 0]
    ]

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.imshow(
        distribution,
        cmap="Greens",
        vmin=0,
        vmax=1
    )

    ax.set_xticks(range(4))
    ax.set_xticklabels(
        ["Chunk 0", "Chunk 1",
         "Chunk 2", "Chunk 3"]
    )

    ax.set_yticks(range(4))
    ax.set_yticklabels(
        ["Peer1", "Peer2", "Peer3", "Peer4"]
    )

    for row in range(4):
        for col in range(4):

            stored = distribution[row][col]

            ax.text(
                col,
                row,
                "Stored" if stored else "-",
                ha="center",
                va="center",
                color="white" if stored else "black"
            )

    ax.set_title("Initial Distributed Chunk Storage")

    save_graph(fig, "chunk_distribution.png")


def export_results():

    rows = [
        ["Active peers", 4, "peers"],
        ["File size", 1048576, "bytes"],
        ["Chunk size", 262144, "bytes"],
        ["Confirmed remote replicas", 8, "chunks"],
        ["Replication time", 0.543, "seconds"],
        ["Normal download time", 2.032, "seconds"],
        ["Owner offline download time", 2.119, "seconds"],
        ["Replication packets sent", 1875, "packets"],
        ["Replication packets acknowledged", 1875, "packets"],
        ["Simulated loss rate", 30, "percent"],
        ["Loss test packets sent", 30, "packets"],
        ["Loss test packets acknowledged", 30, "packets"],
        ["Loss test retransmissions", 49, "packets"],
        ["Loss test simulated drops", 33, "packets"],
        ["Loss test failed packets", 0, "packets"],
        ["File test simulated loss", 10, "percent"],
        ["File loss replication time", 5.616, "seconds"],
        ["File loss packets sent", 1875, "packets"],
        ["File loss packets acknowledged", 1875, "packets"],
        ["File loss retransmissions", 379, "packets"],
        ["File loss simulated drops", 203, "packets"],
        ["File loss failed packets", 0, "packets"],
        ["File loss confirmed replicas", 8, "chunks"],
        ["File loss download time", 2.019, "seconds"]
    ]

    path = RESULTS / "experiment_results.csv"

    with path.open("w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow(
            ["Metric", "Value", "Unit"]
        )

        writer.writerows(rows)

    print("[CSV] Saved:", path)



def plot_file_loss_comparison():

    conditions = ["0% loss", "10% loss"]
    times = [0.543, 5.616]

    fig, ax = plt.subplots(figsize=(8, 5))

    bars = ax.bar(
        conditions, times,
        color=["#16a34a", "#f59e0b"]
    )

    ax.bar_label(bars, fmt="%.3f s")
    ax.set_ylim(0, 6.5)
    ax.set_ylabel("Replication time (seconds)")
    ax.set_title("File Replication Under Packet Loss")
    ax.grid(axis="y", alpha=0.3)

    save_graph(fig, "file_loss_comparison.png")


def plot_file_loss_statistics():

    labels = [
        "Original packets",
        "Acknowledged",
        "Retransmissions",
        "Simulated drops",
        "Failed packets"
    ]

    values = [1875, 1875, 379, 203, 0]

    fig, ax = plt.subplots(figsize=(10, 5))

    bars = ax.bar(
        labels, values,
        color=[
            "#2563eb",
            "#16a34a",
            "#f59e0b",
            "#ef4444",
            "#64748b"
        ]
    )

    ax.bar_label(bars)
    ax.set_ylim(0, 2100)
    ax.set_ylabel("Packet count")
    ax.set_title("File Transfer Under 10% Simulated Loss")
    ax.tick_params(axis="x", rotation=15)
    ax.grid(axis="y", alpha=0.3)

    save_graph(fig, "file_loss_statistics.png")


if __name__ == "__main__":

    print("\n===== RPGP PERFORMANCE ANALYSIS =====")

    plot_delivery_rate()
    plot_retransmissions()
    plot_file_performance()
    plot_chunk_distribution()
    plot_file_loss_comparison()
    plot_file_loss_statistics()
    export_results()

    print("\nPerformance graphs generated successfully!")

