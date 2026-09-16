# Copyright (c) 2024-2026 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Textual statistics for a batch validation run.

This is a port of the ``analyze`` command of the standalone ``report.py`` utility,
adapted to integrate with the validator: it works on the in-memory batch crate
records (``BatchCrateEntry.to_dict()`` output, the same shape stored in a session
file) and renders to a provided :class:`rich.console.Console`. The chart
generation of the original script is intentionally not included.

Each crate is classified into one of three mutually exclusive states:

* ``PASSED`` — validation succeeded (``passed`` is true);
* ``FAILED`` — validation ran and reported one or more issues;
* ``ERROR``  — validation could not run (e.g. a non-RO-Crate input): the crate
  carries an ``error`` message but no issues and no statistics.
"""

from __future__ import annotations

import statistics as _stats
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from rich.console import Console


# Minimum sample sizes for descriptive statistics: quartiles need at least four
# data points, spread measures (stdev/variance) at least two.
_MIN_SAMPLES_FOR_QUARTILES = 4
_MIN_SAMPLES_FOR_SPREAD = 2


# ===========================================================================
# Normalisation and aggregation
# ===========================================================================


def _error_types(issues: list[dict]) -> list[tuple[str, str]]:
    """Distinct ``(check identifier, check name)`` pairs, first-seen order."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for issue in issues:
        chk = issue.get("check") or {}
        cid = chk.get("identifier")
        if cid and cid not in seen:
            seen.add(cid)
            out.append((cid, (chk.get("name") or "").strip()))
    return out


def normalise_crate(crate: dict) -> dict:
    """
    Turn one raw batch crate record (``BatchCrateEntry.to_dict()`` shape) into
    the flat record used by the statistics renderers.
    """
    stats = crate.get("statistics") or {}
    issues = crate.get("issues") or []
    passed = bool(crate.get("passed"))

    if passed:
        status = "PASSED"
    elif issues:
        status = "FAILED"
    else:
        status = "ERROR"

    return {
        "path": crate["path"],
        "name": Path(crate["path"]).name,
        "size_bytes": crate.get("size_bytes"),
        "duration": crate.get("duration"),
        "passed": passed,
        "status": status,
        "error": crate.get("error"),
        "checks": stats.get("total_checks", 0),
        "passed_checks": stats.get("total_passed_checks", 0),
        "issues": issues,
        "n_issues": len(issues),
        # Individual REQUIRED issue lines (the legacy "└─ Required" count).
        "subissues": sum(1 for i in issues if i.get("severity") == "REQUIRED"),
        "error_types": _error_types(issues),
    }


def select(crates: list[dict], include_errors: bool = True) -> list[dict]:
    """Optionally drop the *errored* crates (the spurious, non-RO-Crate inputs)."""
    if include_errors:
        return crates
    return [c for c in crates if c["status"] != "ERROR"]


def passed_crates(crates: list[dict]) -> list[dict]:
    return [c for c in crates if c["status"] == "PASSED"]


def failed_crates(crates: list[dict]) -> list[dict]:
    """Crates that ran validation and reported at least one issue."""
    return [c for c in crates if c["status"] == "FAILED"]


def errored_crates(crates: list[dict]) -> list[dict]:
    return [c for c in crates if c["status"] == "ERROR"]


def crates_per_check(failed: list[dict]) -> tuple[Counter, dict[str, str]]:
    """Number of distinct FAILED crates affected by each check identifier."""
    counter: Counter[str] = Counter()
    names: dict[str, str] = {}
    for crate in failed:
        for code, name in crate["error_types"]:
            counter[code] += 1
            names[code] = name
    return counter, names


# ===========================================================================
# Rich rendering helpers
# ===========================================================================

# Semantic colour palette, shared across all statistics tables/bars so the same
# kind of datum always reads with the same colour:
_C_CRATES = "cyan"  # a neutral count of crates
_C_CHECKS = "blue"  # total checks
_C_PASSED = "green"  # passed checks / passed crates
_C_ISSUES = "red"  # issues / REQUIRED issues / failed-or-affected crates
_C_ERROR = "yellow"  # crates that errored out
_C_DURATION = "yellow"  # validation time
_C_TYPE = "magenta"  # check / issue-type identifiers
_C_CRATE_ID = "bold cyan"  # crate names / ids
_C_PERCENT = "dim"  # percentages / shares


def _rtable(title: str = "") -> Table:
    return Table(
        title=title,
        title_style="bold",
        title_justify="left",
        box=box.SIMPLE_HEAVY,
        header_style="bold",
    )


# All sub-section panel titles share one bold accent colour.
_TITLE_STYLE = "bold yellow"


def _spanel(title: str, description: str, *renderables, title_style: str = _TITLE_STYLE) -> Panel:
    """
    Wrap renderables in a Rich Panel with a bold, coloured title and a brief white
    italic description.
    """
    desc = Text(description, style="white italic")
    return Panel(
        Group(desc, *renderables),
        title=Text(title, style=title_style),
        title_align="left",
        padding=(1, 2),
    )


def _bar(value: float, maxv: float, width: int = 18, color: str = "cyan") -> str:
    """A small horizontal bar made of block characters (for visual scale)."""
    filled = round(width * value / maxv) if maxv else 0
    return f"[{color}]{'█' * filled}[/][dim]{'·' * (width - filled)}[/]"


def _describe_lines(
    values: list[float],
    *,
    value_style: str,
    unit: str = "",
    count_style: str = _C_CRATES,
) -> list[Text]:
    """
    Build the three ``Range`` / ``Central`` / ``Spread`` descriptive-statistics
    lines for a numeric series, used by both the issue-count and duration
    sections so they share one consistent presentation.

    ``value_style`` colours the metric values; ``unit`` is appended to each value
    (e.g. ``"s"`` for durations); ``count_style`` colours the sample size ``n``.
    """
    n = len(values)
    ordered = sorted(values)
    total = sum(values)
    mean_val = _stats.mean(values)
    median_val = _stats.median(values)
    if n >= _MIN_SAMPLES_FOR_QUARTILES:
        q1_val, _, q3_val = _stats.quantiles(values, n=4)
    else:
        q1_val, q3_val = ordered[0], ordered[-1]
    iqr_val = q3_val - q1_val
    std_val = _stats.stdev(values) if n >= _MIN_SAMPLES_FOR_SPREAD else 0.0
    var_val = _stats.variance(values) if n >= _MIN_SAMPLES_FOR_SPREAD else 0.0

    def r(x: float) -> str:  # range values: integer when whole, else 2 decimals
        body = f"{int(x)}" if float(x).is_integer() else f"{x:.2f}"
        return f"[bold {value_style}]{body}{unit}[/]"

    def f(x: float) -> str:  # central/spread values: always 2 decimals
        return f"[bold {value_style}]{x:.2f}{unit}[/]"

    return [
        Text.from_markup(
            f"[bold orange3]Range[/]   →   total={r(total)}   "
            f"n=[bold {count_style}]{n}[/]   min={r(ordered[0])}   max={r(ordered[-1])}"
        ),
        Text.from_markup(
            f"[bold orange3]Central[/] →   mean={f(mean_val)}   median={f(median_val)}   "
            f"Q1={f(q1_val)}   Q3={f(q3_val)}"
        ),
        Text.from_markup(
            f"[bold orange3]Spread[/]  →   stddev={f(std_val)}   variance={f(var_val)}   IQR={f(iqr_val)}"
        ),
    ]


def _print_summary_table(con: Console, crates: list[dict]) -> None:
    """Print a compact, coloured PASSED/FAILED/ERROR summary."""
    total = len(crates)
    rows = [
        ("PASSED", len(passed_crates(crates)), "green"),
        ("FAILED", len(failed_crates(crates)), "red"),
        ("ERROR", len(errored_crates(crates)), "yellow"),
    ]
    table = _rtable()
    table.add_column("Status")
    table.add_column("Crates", justify="right")
    table.add_column("Share", justify="right")
    table.add_column("", justify="left")
    for label, n, color in rows:
        pct = 100 * n / total if total else 0
        table.add_row(f"[{color}]{label}[/]", f"[{color}]{n}[/]", f"{pct:.1f}%", _bar(n, total, color=color))
    table.add_section()
    table.add_row("[bold]TOTAL[/]", f"[bold]{total}[/]", "100.0%", "")
    con.print(_spanel("Outcome Summary", "Overall outcome across all analysed crates", table))


def _render_overview(con: Console, crates, failed, errored) -> None:
    if failed:
        issues = [c["n_issues"] for c in failed]
        t = _rtable()
        t.add_column("Issues/crate", justify="right")
        t.add_column("Crates", justify="right")
        t.add_column("")
        dist = Counter(issues)
        maxv = max(dist.values())
        for k, v in sorted(dist.items()):
            t.add_row(f"[{_C_ISSUES}]{k}[/]", f"[{_C_CRATES}]{v}[/]", _bar(v, maxv, color=_C_CRATES))
        con.print(
            _spanel(
                "Issues Per Crate (Failed)",
                "Distribution of issue counts among crates that did not pass validation",
                t,
                Text(""),
                *_describe_lines(issues, value_style=_C_ISSUES),
            )
        )

    combos = Counter((c["checks"], c["passed_checks"]) for c in crates)
    t = _rtable()
    t.add_column("Crates", justify="right")
    t.add_column("Checks", justify="right")
    t.add_column("Passed", justify="right")
    for (chk, ps), v in combos.most_common():
        t.add_row(f"[bold {_C_CRATES}]{v}[/]", f"[bold {_C_CHECKS}]{chk}[/]", f"[bold {_C_PASSED}]{ps}[/]")
    con.print(
        _spanel(
            "Checks/Passed Combinations",
            "Number of crates sharing the same total checks and passed checks",
            t,
        )
    )

    if errored:
        t = _rtable()
        t.add_column("Crates", justify="right")
        t.add_column("Reason", style="yellow")
        for reason, v in Counter(c["error"] for c in errored).most_common():
            t.add_row(f"[bold {_C_ERROR}]{v}[/]", reason or "(no message)")
        con.print(
            _spanel(
                "Validation Errors",
                "Crates that encountered errors during validation and produced no results",
                t,
            )
        )


def _render_error_types(con: Console, failed) -> None:
    counter, names = crates_per_check(failed)
    total = len(failed)
    maxv = max(counter.values()) if counter else 1
    t = _rtable()
    t.add_column("Check", style=_C_TYPE, no_wrap=True)
    t.add_column("Crates", justify="right")
    t.add_column("Share", justify="right")
    t.add_column("")
    t.add_column("Description")
    for code, cnt in counter.most_common():
        pct = 100 * cnt / total if total else 0
        t.add_row(
            code,
            f"[bold {_C_ISSUES}]{cnt}[/]",
            f"[{_C_PERCENT}]{pct:.1f}%[/]",
            _bar(cnt, maxv, color=_C_ISSUES),
            names[code],
        )
    single = sum(1 for c in failed if len(c["error_types"]) == 1)
    multi = sum(1 for c in failed if len(c["error_types"]) > 1)
    con.print(
        _spanel(
            "Error-Type Distribution",
            "How many crates are affected by each type of validation error",
            t,
            Text(""),
            Text.from_markup(
                f"Crates with exactly 1 error type: [bold {_C_CRATES}]{single}[/]   "
                f"more than one: [bold {_C_CRATES}]{multi}[/]"
            ),
        )
    )


def _render_issue_attribution(con: Console, failed) -> None:
    single_attrib: Counter[str] = Counter()
    multi_crates: list[dict] = []
    total_subs = 0
    for crate in failed:
        total_subs += crate["subissues"]
        if len(crate["error_types"]) == 1:
            single_attrib[crate["error_types"][0][0]] += crate["subissues"]
        elif len(crate["error_types"]) > 1:
            multi_crates.append(crate)

    renderables: list = [
        Text.from_markup(f"Total REQUIRED issues: [bold {_C_ISSUES}]{total_subs}[/]"),
    ]

    if single_attrib:
        maxv = max(single_attrib.values())
        t = _rtable()
        t.add_column("Check", style=_C_TYPE, no_wrap=True)
        t.add_column("REQUIRED Issues", justify="right")
        t.add_column("")
        for code, cnt in sorted(single_attrib.items(), key=lambda x: -x[1]):
            t.add_row(code, f"[bold {_C_ISSUES}]{cnt}[/]", _bar(cnt, maxv, color=_C_ISSUES))
        renderables.append(Text(""))
        renderables.append(t)

    if multi_crates:
        t = _rtable()
        t.add_column("Crate", style=_C_CRATE_ID, no_wrap=True)
        t.add_column("REQUIRED Issues", justify="right")
        t.add_column("Types", style=_C_TYPE)
        for c in multi_crates:
            types = ", ".join(code for code, _ in c["error_types"])
            t.add_row(c["name"], f"[bold {_C_ISSUES}]{c['subissues']}[/]", types)
        renderables.append(Text(""))
        renderables.append(t)

    con.print(
        _spanel(
            "Issue Attribution",
            "Detailed breakdown of REQUIRED issues by check type",
            *renderables,
        )
    )


def _render_durations(con: Console, failed, top_n: int) -> None:
    durations = [(c["duration"], c) for c in failed if c.get("duration") is not None]
    if not durations:
        return
    vals = [d for d, _ in durations]
    t = _rtable()
    t.add_column("Crate", style=_C_CRATE_ID, no_wrap=True)
    t.add_column("Duration", justify="right")
    t.add_column("REQUIRED Issues", justify="right")
    for dur, c in sorted(durations, key=lambda x: -x[0])[:top_n]:
        t.add_row(c["name"], f"[bold {_C_DURATION}]{dur:.2f}s[/]", f"[bold {_C_ISSUES}]{c['subissues']}[/]")
    con.print(
        _spanel(
            "Slowest Crates",
            f"Top {top_n} crates with the longest validation durations",
            t,
            Text(""),
            *_describe_lines(vals, value_style=_C_DURATION, unit="s"),
        )
    )


def _render_outliers(con: Console, failed, threshold: int) -> None:
    outliers = sorted(
        [c for c in failed if c["subissues"] >= threshold],
        key=lambda x: -x["subissues"],
    )
    if not outliers:
        con.print(
            _spanel(
                f"Outlier Crates (≥ {threshold} REQUIRED issues)",
                "Crates with an unusually high number of REQUIRED issues",
                Text.from_markup(f"[dim]No outlier crates with ≥ {threshold} REQUIRED issues.[/]"),
            )
        )
        return
    t = _rtable()
    t.add_column("Crate", style=_C_CRATE_ID, no_wrap=True)
    t.add_column("REQUIRED Issues", justify="right")
    t.add_column("Types", style=_C_TYPE)
    for c in outliers:
        types = ", ".join(code for code, _ in c["error_types"])
        t.add_row(c["name"], f"[bold {_C_ISSUES}]{c['subissues']}[/]", types)
    con.print(
        _spanel(
            f"Outlier Crates (≥ {threshold} REQUIRED issues)",
            "Crates with an unusually high number of REQUIRED issues",
            t,
        )
    )


def _render_detailed(con: Console, crates, failed, errored, top_n: int, outlier_threshold: int) -> None:
    _render_overview(con, crates, failed, errored)
    if failed:
        con.print()
        _render_error_types(con, failed)
        con.print()
        _render_issue_attribution(con, failed)
        con.print()
        _render_durations(con, failed, top_n)
        con.print()
        _render_outliers(con, failed, outlier_threshold)


# ===========================================================================
# Public entry point
# ===========================================================================


def render_statistics(
    console: Console,
    crate_dicts: list[dict],
    *,
    include_errors: bool = True,
    top_n: int = 10,
    outlier_threshold: int = 5,
) -> None:
    """
    Render the textual batch statistics for ``crate_dicts`` to ``console``.

    :param console: target console (the validator's Rich console)
    :param crate_dicts: raw crate records (``BatchCrateEntry.to_dict()`` shape)
    :param include_errors: include the crates that could not be validated at all
    :param top_n: how many of the slowest crates to list
    :param outlier_threshold: minimum individual issues for a crate to be an outlier
    """
    all_crates = [normalise_crate(c) for c in crate_dicts]
    crates = select(all_crates, include_errors=include_errors)
    failed = failed_crates(crates)
    errored = errored_crates(crates)

    # Separate the statistics section from whatever was printed before it.
    console.print()
    console.print()
    console.rule("[bold cyan]Statistics[/]")
    analysed = f"Crates analysed: [bold cyan]{len(crates)}[/]"
    if errored:
        analysed += f"   [dim]·[/dim]   [bold red]{len(errored)}[/] could not be validated [dim](ERROR)[/dim]"
    console.print(analysed)
    console.print()
    _print_summary_table(console, crates)
    console.print()
    _render_detailed(console, crates, failed, errored, top_n, outlier_threshold)


# ===========================================================================
# Markdown file output
# ===========================================================================


def _md_table(headers: list[str], rows: list[list[str]], align_left: list[int] | None = None) -> str:
    """Build a GF markdown table from headers and row data."""
    out: list[str] = []
    out.append("| " + " | ".join(headers) + " |")
    separators: list[str] = []
    for i, h in enumerate(headers):
        if align_left and i in align_left:
            separators.append(":" + "-" * (len(h) + 0))
        else:
            separators.append("-" * (len(h) + 0))
    out.append("| " + " | ".join(separators) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out) + "\n"


def _md_describe_lines(values: list[float], *, unit: str = "") -> str:
    """Descriptive stats lines in markdown format."""
    n = len(values)
    ordered = sorted(values)
    total = sum(values)
    mean_val = _stats.mean(values)
    median_val = _stats.median(values)
    if n >= _MIN_SAMPLES_FOR_QUARTILES:
        q1_val, _, q3_val = _stats.quantiles(values, n=4)
    else:
        q1_val, q3_val = ordered[0], ordered[-1]
    iqr_val = q3_val - q1_val
    std_val = _stats.stdev(values) if n >= _MIN_SAMPLES_FOR_SPREAD else 0.0
    var_val = _stats.variance(values) if n >= _MIN_SAMPLES_FOR_SPREAD else 0.0

    def r(x: float) -> str:
        return f"{int(x)}" if float(x).is_integer() else f"{x:.2f}"

    def f(x: float) -> str:
        return f"{x:.2f}"

    lines: list[str] = []
    lines.append(
        f"- **Range**   →   total={r(total)}{unit}   n={n}   min={r(ordered[0])}{unit}   max={r(ordered[-1])}{unit}"
    )
    lines.append(
        f"- **Central** →   mean={f(mean_val)}{unit}   median={f(median_val)}{unit}   "
        f"Q1={f(q1_val)}{unit}   Q3={f(q3_val)}{unit}"
    )
    lines.append(f"- **Spread**  →   stddev={f(std_val)}{unit}   variance={f(var_val)}{unit}   IQR={f(iqr_val)}{unit}")
    return "\n".join(lines) + "\n"


def render_statistics_md(
    file,
    crate_dicts: list[dict],
    *,
    include_errors: bool = True,
    top_n: int = 10,
    outlier_threshold: int = 5,
) -> None:
    """Write batch statistics to *file* in markdown format."""
    all_crates = [normalise_crate(c) for c in crate_dicts]
    crates = select(all_crates, include_errors=include_errors)
    failed = failed_crates(crates)
    errored = errored_crates(crates)

    w = file.write

    w("# Validation Statistics\n\n")
    _md_write_summary_line(w, crates, errored)
    _md_write_outcome_summary(w, crates, failed, errored)
    _md_write_issues_per_crate(w, failed)
    _md_write_checks_combos(w, crates)
    _md_write_validation_errors(w, errored)
    _md_write_error_types(w, failed)
    _md_write_issue_attribution(w, failed)
    _md_write_slowest(w, failed, top_n)
    _md_write_outliers(w, failed, outlier_threshold)


def _md_write_summary_line(w, crates, errored) -> None:
    analysed = f"Crates analysed: **{len(crates)}**"
    if errored:
        analysed += f" · **{len(errored)}** could not be validated (ERROR)"
    w(analysed + "\n\n")


def _md_write_outcome_summary(w, crates, failed, errored) -> None:
    w("## Outcome Summary\n\n")
    total = len(crates)
    rows: list[list[str]] = []
    for label, n in [("PASSED", len(passed_crates(crates))), ("FAILED", len(failed)), ("ERROR", len(errored))]:
        pct = 100 * n / total if total else 0
        rows.append([label, str(n), f"{pct:.1f}%"])
    rows.append(["**TOTAL**", f"**{total}**", "**100.0%**"])
    w(_md_table(["Status", "Crates", "Share"], rows, align_left=[0]))
    w("\n")


def _md_write_issues_per_crate(w, failed) -> None:
    if not failed:
        return
    issues = [c["n_issues"] for c in failed]
    w("## Issues Per Crate (Failed)\n\n")
    dist = Counter(issues)
    rows = [[str(k), str(v)] for k, v in sorted(dist.items())]
    w(_md_table(["Issues/crate", "Crates"], rows))
    w("\n")
    w(_md_describe_lines(issues))
    w("\n")


def _md_write_checks_combos(w, crates) -> None:
    w("## Checks/Passed Combinations\n\n")
    combos = Counter((c["checks"], c["passed_checks"]) for c in crates)
    rows = [[str(v), str(chk), str(ps)] for (chk, ps), v in combos.most_common()]
    w(_md_table(["Crates", "Checks", "Passed"], rows))
    w("\n")


def _md_write_validation_errors(w, errored) -> None:
    if not errored:
        return
    w("## Validation Errors\n\n")
    rows = []
    for reason, v in Counter(c["error"] for c in errored).most_common():
        rows.append([str(v), reason or "(no message)"])
    w(_md_table(["Crates", "Reason"], rows, align_left=[1]))
    w("\n")


def _md_write_error_types(w, failed) -> None:
    if not failed:
        return
    w("## Error-Type Distribution\n\n")
    counter, names = crates_per_check(failed)
    total_f = len(failed)
    rows = []
    for code, cnt in counter.most_common():
        pct = 100 * cnt / total_f if total_f else 0
        rows.append([code, str(cnt), f"{pct:.1f}%", names[code]])
    w(_md_table(["Check", "Crates", "Share", "Description"], rows, align_left=[0, 3]))
    single = sum(1 for c in failed if len(c["error_types"]) == 1)
    multi = sum(1 for c in failed if len(c["error_types"]) > 1)
    w(f"\nCrates with exactly 1 error type: **{single}**  more than one: **{multi}**\n\n")


def _md_write_issue_attribution(w, failed) -> None:
    if not failed:
        return
    w("## Issue Attribution\n\n")
    single_attrib: Counter[str] = Counter()
    multi_crates: list[dict] = []
    total_subs = 0
    for crate in failed:
        total_subs += crate["subissues"]
        if len(crate["error_types"]) == 1:
            single_attrib[crate["error_types"][0][0]] += crate["subissues"]
        elif len(crate["error_types"]) > 1:
            multi_crates.append(crate)
    w(f"Total REQUIRED issues: **{total_subs}**\n\n")
    if single_attrib:
        rows = [[code, str(cnt)] for code, cnt in sorted(single_attrib.items(), key=lambda x: -x[1])]
        w(_md_table(["Check", "REQUIRED Issues"], rows, align_left=[0]))
        w("\n")
    if multi_crates:
        rows = [[c["name"], str(c["subissues"]), ", ".join(code for code, _ in c["error_types"])] for c in multi_crates]
        w(_md_table(["Crate", "REQUIRED Issues", "Types"], rows, align_left=[0, 2]))
        w("\n")


def _md_write_slowest(w, failed, top_n) -> None:
    if not failed:
        return
    durations = [(c["duration"], c) for c in failed if c.get("duration") is not None]
    if not durations:
        return
    w("## Slowest Crates\n\n")
    vals = [d for d, _ in durations]
    rows = []
    for dur, c in sorted(durations, key=lambda x: -x[0])[:top_n]:
        rows.append([c["name"], f"{dur:.2f}s", str(c["subissues"])])
    w(_md_table(["Crate", "Duration", "REQUIRED Issues"], rows, align_left=[0]))
    w("\n")
    w(_md_describe_lines(vals, unit="s"))
    w("\n")


def _md_write_outliers(w, failed, outlier_threshold) -> None:
    if not failed:
        return
    outliers = sorted(
        [c for c in failed if c["subissues"] >= outlier_threshold],
        key=lambda x: -x["subissues"],
    )
    w(f"## Outlier Crates (≥ {outlier_threshold} REQUIRED issues)\n\n")
    if not outliers:
        w(f"No outlier crates with ≥ {outlier_threshold} REQUIRED issues.\n\n")
    else:
        rows = [[c["name"], str(c["subissues"]), ", ".join(code for code, _ in c["error_types"])] for c in outliers]
        w(_md_table(["Crate", "REQUIRED Issues", "Types"], rows, align_left=[0, 2]))
        w("\n")
