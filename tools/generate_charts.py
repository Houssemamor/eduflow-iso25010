"""Generate evidence charts from real tool outputs (no invented numbers)."""
import csv
import os
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "evidence")
CHARTS = os.path.join(EVIDENCE, "charts")
os.makedirs(CHARTS, exist_ok=True)

COLORS = {
    "primary": "#2563eb",
    "good": "#16a34a",
    "warn": "#d97706",
    "grid": "#e2e8f0",
    "text": "#1e293b",
}


def style(axis):
    axis.set_facecolor("white")
    axis.grid(axis="y", color=COLORS["grid"], linewidth=0.8)
    axis.set_axisbelow(True)
    axis.spines[["top", "right"]].set_visible(False)
    axis.tick_params(colors=COLORS["text"], labelsize=9)


def performance_chart():
    path = os.path.join(EVIDENCE, "perf_stats.csv")
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if not row.get("Name"):
                continue
            rows.append(row)
    labels = [row["Name"].replace("/api/v1/", "") for row in rows if row["Name"] != "Aggregated"]
    p95 = [float(row["95%"]) for row in rows if row["Name"] != "Aggregated"]

    fig, axis = plt.subplots(figsize=(8, 4.2))
    bars = axis.bar(labels, p95, color=COLORS["primary"], width=0.55)
    axis.axhline(500, color=COLORS["warn"], linestyle="--", linewidth=1.5,
                 label="Target: 500 ms at 20 users")
    for bar, value in zip(bars, p95):
        axis.text(bar.get_x() + bar.get_width() / 2, value + 8, f"{value:.0f} ms",
                  ha="center", fontsize=9, color=COLORS["text"])
    axis.set_ylabel("p95 response time (ms)")
    axis.set_title("Locust p95 response time by endpoint (20 users, 30 s)")
    axis.legend(frameon=False, fontsize=9)
    style(axis)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, "performance_p95.png"), dpi=150)
    plt.close(fig)
    return rows


def coverage_chart():
    path = os.path.join(EVIDENCE, "coverage.xml")
    root = ET.parse(path).getroot()
    data = []
    for cls in root.iter("class"):
        filename = cls.attrib["filename"].replace("app\\", "").replace("app/", "")
        lines = list(cls.iter("line"))
        if not lines:
            continue
        covered = sum(1 for line in lines if int(line.attrib.get("hits", "0")) > 0)
        data.append((filename, 100 * covered / len(lines)))
    data.sort(key=lambda item: item[1])
    total = root.attrib.get("line-rate", 0)
    if isinstance(total, str):
        total = float(total) * 100

    fig, axis = plt.subplots(figsize=(8, 4.2))
    names = [name for name, _ in data]
    values = [value for _, value in data]
    axis.barh(names, values, color=COLORS["good"], height=0.6)
    for index, value in enumerate(values):
        axis.text(value + 1, index, f"{value:.0f}%", va="center", fontsize=9)
    axis.axvline(80, color=COLORS["warn"], linestyle="--", linewidth=1.5,
                 label="Target: 80%")
    axis.set_xlim(0, 108)
    axis.set_xlabel("Line coverage (%)")
    axis.set_title(f"pytest-cov line coverage by module (total {total:.0f}%)")
    axis.legend(frameon=False, fontsize=9, loc="lower right")
    style(axis)
    axis.grid(axis="x", color=COLORS["grid"], linewidth=0.8)
    axis.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, "coverage_by_module.png"), dpi=150)
    plt.close(fig)
    return total


def _test_cases(name: str) -> list[tuple[str, str]]:
    root = ET.parse(os.path.join(EVIDENCE, name)).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    return [
        (case.attrib["classname"], case.attrib["name"])
        for case in suite.findall("testcase")
    ]


def tests_by_check() -> list[tuple[str, int]]:
    """Count executed tests grouped by test / check, matching the toolkit matrix."""
    unit = _test_cases("unit.xml")
    api = _test_cases("api.xml")
    e2e = _test_cases("e2e.xml")
    simulation = _test_cases("simulation.xml")

    def in_prefix(cases, prefix):
        return sum(1 for classname, _ in cases if classname.startswith(prefix))

    return [
        ("Unit - business rules", len(unit)),
        ("API contract", in_prefix(api, "tests.api.")),
        ("Integration flows", in_prefix(api, "tests.integration.")),
        ("Reliability", in_prefix(api, "tests.reliability.")),
        ("Fuzz / property", in_prefix(api, "tests.fuzz.")),
        ("Smoke", in_prefix(api, "tests.smoke.")),
        ("E2E journeys", in_prefix(e2e, "tests.e2e.test_ui")),
        ("Accessibility", in_prefix(e2e, "tests.e2e.test_accessibility")),
        ("Dashboard simulation", len(simulation)),
    ]


def test_counts_chart():
    counts = tests_by_check()
    total = sum(value for _, value in counts)

    fig, axis = plt.subplots(figsize=(9, 5.2))
    labels = [label for label, _ in counts]
    values = [value for _, value in counts]
    axis.barh(labels, values, color=COLORS["primary"], height=0.6)
    for index, value in enumerate(values):
        axis.text(value + 0.3, index, str(value), va="center", fontsize=9,
                  color=COLORS["text"])
    axis.set_xlabel("Automated tests passed")
    axis.set_title("Automated tests executed by test / check (total %d)" % total)
    axis.set_xlim(0, max(values) + 4)
    style(axis)
    axis.grid(axis="x", color=COLORS["grid"], linewidth=0.8)
    axis.grid(axis="y", visible=False)
    axis.invert_yaxis()
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, "tests_by_layer.png"), dpi=150)
    plt.close(fig)
    return counts


if __name__ == "__main__":
    perf_rows = performance_chart()
    coverage_total = coverage_chart()
    counts = test_counts_chart()
    print(f"Charts written to {CHARTS}")
    print(f"Performance rows: {len(perf_rows)}, coverage: {coverage_total:.1f}%")
    print("Test counts:", counts)
