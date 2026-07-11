"""
morning_report.py

PATCC Command Center v0.1

Purpose
-------
Runs the existing PATCC scoring engine for a configurable watchlist and creates:

    Reports/latest/morning_report.txt
    Reports/latest/morning_report.html
    Reports/latest/morning_report.json

It also archives every generated report by date and time.

This first version deliberately calls the existing scoring engine through its
working command-line interface. That avoids duplicating calculations or tightly
coupling the report to internal class signatures while PATCC is evolving.

Run examples
------------
python -m Core.morning_report

python -m Core.morning_report --open

python -m Core.morning_report --tickers SPY QQQ IWM UNG GLD

python -m Core.morning_report --tickers SPY QQQ SOXL TQQQ --tf 1d --open
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import webbrowser

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = PROJECT_ROOT / "Reports"
LATEST_DIR = REPORTS_ROOT / "latest"
ARCHIVE_DIR = REPORTS_ROOT / "archive"
MONTHLY_DIR = REPORTS_ROOT / "monthly"
ERRORS_DIR = REPORTS_ROOT / "errors"

DEFAULT_RETENTION_DAYS = 90
ERROR_RETENTION_DAYS = 30


DEFAULT_WATCHLIST = [
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
    "VIXY",
    "GLD",
    "SLV",
    "USO",
    "UNG",
    "BTC-USD",
]

EASTERN_TIME = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TickerReport:
    ticker: str
    timeframe: str
    status: str
    score: int | None
    grade: str
    action: str
    price: float | None
    provider: str
    market_state: str
    trend: str
    error: str
    raw_output: str


@dataclass
class MorningReport:
    report_version: str
    generated_at_et: str
    generated_at_iso: str
    timeframe: str
    watchlist: list[str]
    successful_scans: int
    failed_scans: int
    market_posture: str
    average_score: float | None
    strongest_tickers: list[str]
    weakest_tickers: list[str]
    ticker_reports: list[TickerReport]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def ensure_directories() -> None:
    """Create all PATCC report directories."""
    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)

def safe_report_path(path: Path) -> bool:
    """
    Confirm that a path is located inside the PATCC Reports directory.

    This prevents accidental deletion outside Reports.
    """
    try:
        path.resolve().relative_to(REPORTS_ROOT.resolve())
        return True
    except ValueError:
        return False


def parse_archive_date(folder: Path) -> datetime | None:
    """
    Parse an archive folder named YYYY-MM-DD.

    Returns None when the folder name is not a valid archive date.
    """
    try:
        return datetime.strptime(folder.name, "%Y-%m-%d")
    except ValueError:
        return None


def cleanup_old_archives(
    retention_days: int,
    dry_run: bool = False,
) -> list[str]:
    """
    Remove dated archive directories older than the retention period.

    Safety protections:
    - Never touches Reports/latest
    - Never touches Reports/monthly
    - Never removes today's archive
    - Never removes anything outside Reports
    """
    ensure_directories()

    now_et = datetime.now(EASTERN_TIME)
    today = now_et.date()
    cutoff_date = today.fromordinal(today.toordinal() - retention_days)

    actions: list[str] = []

    for date_folder in sorted(ARCHIVE_DIR.iterdir()):
        if not date_folder.is_dir():
            continue

        archive_datetime = parse_archive_date(date_folder)

        if archive_datetime is None:
            actions.append(
                f"SKIPPED unrecognized archive folder: {date_folder}"
            )
            continue

        archive_date = archive_datetime.date()

        if archive_date == today:
            actions.append(
                f"KEPT today's archive: {date_folder}"
            )
            continue

        if archive_date >= cutoff_date:
            continue

        if not safe_report_path(date_folder):
            actions.append(
                f"SAFETY BLOCKED deletion outside Reports: {date_folder}"
            )
            continue

        if dry_run:
            actions.append(
                f"DRY RUN would delete archive: {date_folder}"
            )
        else:
            shutil.rmtree(date_folder)
            actions.append(
                f"DELETED archive: {date_folder}"
            )

    return actions


def cleanup_old_error_reports(
    retention_days: int = ERROR_RETENTION_DAYS,
    dry_run: bool = False,
) -> list[str]:
    """
    Remove error-report files and folders older than the retention period.
    """
    ensure_directories()

    now_timestamp = datetime.now(EASTERN_TIME).timestamp()
    retention_seconds = retention_days * 24 * 60 * 60

    actions: list[str] = []

    for item in sorted(ERRORS_DIR.iterdir()):
        try:
            age_seconds = now_timestamp - item.stat().st_mtime
        except OSError as exc:
            actions.append(
                f"SKIPPED unreadable error item {item}: {exc}"
            )
            continue

        if age_seconds <= retention_seconds:
            continue

        if not safe_report_path(item):
            actions.append(
                f"SAFETY BLOCKED deletion outside Reports: {item}"
            )
            continue

        if dry_run:
            actions.append(
                f"DRY RUN would delete error item: {item}"
            )
            continue

        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

        actions.append(
            f"DELETED error item: {item}"
        )

    return actions


def run_report_cleanup(
    archive_retention_days: int,
    dry_run: bool = False,
) -> list[str]:
    """Run all PATCC report cleanup policies."""
    actions = []

    actions.extend(
        cleanup_old_archives(
            retention_days=archive_retention_days,
            dry_run=dry_run,
        )
    )

    actions.extend(
        cleanup_old_error_reports(
            retention_days=ERROR_RETENTION_DAYS,
            dry_run=dry_run,
        )
    )

    if not actions:
        actions.append(
            "No reports qualified for cleanup."
        )

    return actions


def normalize_tickers(tickers: Iterable[str]) -> list[str]:
    """
    Normalize symbols, remove blanks, and preserve first-seen order.
    """
    normalized: list[str] = []
    seen: set[str] = set()

    for ticker in tickers:
        symbol = ticker.strip().upper()

        if not symbol:
            continue

        if symbol not in seen:
            seen.add(symbol)
            normalized.append(symbol)

    return normalized


def extract_text(
    output: str,
    patterns: list[str],
    default: str = "Not available",
) -> str:
    """
    Return the first captured value from a list of regular expressions.
    """
    for pattern in patterns:
        match = re.search(pattern, output, flags=re.IGNORECASE | re.MULTILINE)

        if match:
            value = match.group(1).strip()

            if value:
                return value

    return default


def extract_integer(output: str, patterns: list[str]) -> int | None:
    """Extract an integer from the scoring-engine output."""
    value = extract_text(output, patterns, default="")

    if not value:
        return None

    match = re.search(r"-?\d+", value)

    if not match:
        return None

    try:
        return int(match.group())
    except ValueError:
        return None


def extract_float(output: str, patterns: list[str]) -> float | None:
    """Extract a floating-point number from the scoring-engine output."""
    value = extract_text(output, patterns, default="")

    if not value:
        return None

    cleaned = value.replace(",", "").replace("$", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)

    if not match:
        return None

    try:
        return float(match.group())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Existing PATCC scoring engine integration
# ---------------------------------------------------------------------------

def run_scoring_engine(
    ticker: str,
    timeframe: str,
    timeout_seconds: int,
) -> TickerReport:
    """
    Run the existing PATCC scoring engine as a Python module.

    Using the established CLI protects the Morning Report from internal
    scoring-engine implementation changes.
    """
    command = [
        sys.executable,
        "-m",
        "Core.scoring_engine",
        "--ticker",
        ticker,
        "--tf",
        timeframe,
    ]

    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""

        combined_output = stdout.strip()

        if stderr.strip():
            if combined_output:
                combined_output += "\n\n"
            combined_output += "STDERR\n------\n" + stderr.strip()

        if completed.returncode != 0:
            return TickerReport(
                ticker=ticker,
                timeframe=timeframe,
                status="FAILED",
                score=None,
                grade="N/A",
                action="ERROR",
                price=None,
                provider="Not available",
                market_state="Not available",
                trend="Not available",
                error=(
                    f"Scoring engine returned exit code "
                    f"{completed.returncode}."
                ),
                raw_output=combined_output,
            )

        score = extract_integer(
            stdout,
            [
                r"Overall\s+Score\s*:\s*([^\r\n]+)",
                r"Composite\s+Score\s*:\s*([^\r\n]+)",
                r"Score\s*:\s*([^\r\n]+)",
            ],
        )

        grade = extract_text(
            stdout,
            [
                r"Grade\s*:\s*([^\r\n]+)",
                r"Rating\s*:\s*([^\r\n]+)",
            ],
        )

        action = extract_text(
            stdout,
            [
                r"Action\s*:\s*([^\r\n]+)",
                r"Recommendation\s*:\s*([^\r\n]+)",
                r"Decision\s*:\s*([^\r\n]+)",
            ],
        )

        price = extract_float(
            stdout,
            [
                r"Last\s+Price\s*:\s*([^\r\n]+)",
                r"Current\s+Price\s*:\s*([^\r\n]+)",
                r"Close\s*:\s*([^\r\n]+)",
            ],
        )

        provider = extract_text(
            stdout,
            [
                r"Provider\s*:\s*([^\r\n]+)",
                r"Data\s+Provider\s*:\s*([^\r\n]+)",
            ],
        )

        market_state = extract_text(
            stdout,
            [
                r"Market\s+State\s*:\s*([^\r\n]+)",
                r"Regime\s*:\s*([^\r\n]+)",
            ],
        )

        trend = extract_text(
            stdout,
            [
                r"Trend\s*:\s*([^\r\n]+)",
                r"Trend\s+State\s*:\s*([^\r\n]+)",
                r"Primary\s+Trend\s*:\s*([^\r\n]+)",
            ],
        )

        return TickerReport(
            ticker=ticker,
            timeframe=timeframe,
            status="SUCCESS",
            score=score,
            grade=grade,
            action=action,
            price=price,
            provider=provider,
            market_state=market_state,
            trend=trend,
            error="",
            raw_output=stdout.strip(),
        )

    except subprocess.TimeoutExpired as exc:
        partial_output = ""

        if exc.stdout:
            partial_output += str(exc.stdout)

        if exc.stderr:
            partial_output += "\n" + str(exc.stderr)

        return TickerReport(
            ticker=ticker,
            timeframe=timeframe,
            status="FAILED",
            score=None,
            grade="N/A",
            action="TIMEOUT",
            price=None,
            provider="Not available",
            market_state="Not available",
            trend="Not available",
            error=f"Scan exceeded {timeout_seconds} seconds.",
            raw_output=partial_output.strip(),
        )

    except OSError as exc:
        return TickerReport(
            ticker=ticker,
            timeframe=timeframe,
            status="FAILED",
            score=None,
            grade="N/A",
            action="ERROR",
            price=None,
            provider="Not available",
            market_state="Not available",
            trend="Not available",
            error=f"Unable to start scoring engine: {exc}",
            raw_output="",
        )


# ---------------------------------------------------------------------------
# Report interpretation
# ---------------------------------------------------------------------------

def determine_market_posture(
    ticker_reports: list[TickerReport],
) -> tuple[str, float | None]:
    """
    Produce an initial portfolio-level posture from available scores.

    This is intentionally simple for v0.1. It will later be replaced by the
    dedicated PATCC Macro and Market Regime engines.
    """
    scores = [
        report.score
        for report in ticker_reports
        if report.status == "SUCCESS" and report.score is not None
    ]

    if not scores:
        return "INSUFFICIENT DATA", None

    average_score = round(sum(scores) / len(scores), 1)

    if average_score >= 80:
        posture = "RISK-ON — FAVOR SELECTIVE HIGH-QUALITY SETUPS"
    elif average_score >= 65:
        posture = "MODERATELY BULLISH — USE NORMAL RISK CONTROLS"
    elif average_score >= 50:
        posture = "NEUTRAL — WAIT FOR CONFIRMATION"
    elif average_score >= 35:
        posture = "DEFENSIVE — REDUCE POSITION SIZE"
    else:
        posture = "RISK-OFF — CAPITAL PRESERVATION PRIORITY"

    return posture, average_score


def ranked_symbols(
    ticker_reports: list[TickerReport],
    reverse: bool,
    limit: int = 3,
) -> list[str]:
    """Return highest- or lowest-ranked symbols with valid scores."""
    scored = [
        report
        for report in ticker_reports
        if report.status == "SUCCESS" and report.score is not None
    ]

    scored.sort(
        key=lambda report: report.score or 0,
        reverse=reverse,
    )

    return [report.ticker for report in scored[:limit]]


def build_report(
    ticker_reports: list[TickerReport],
    timeframe: str,
    watchlist: list[str],
) -> MorningReport:
    """Assemble the complete report object."""
    now_et = datetime.now(EASTERN_TIME)
    posture, average_score = determine_market_posture(ticker_reports)

    successful = sum(
        1 for report in ticker_reports if report.status == "SUCCESS"
    )
    failed = len(ticker_reports) - successful

    return MorningReport(
        report_version="0.1.0",
        generated_at_et=now_et.strftime("%A, %B %d, %Y at %I:%M:%S %p ET"),
        generated_at_iso=now_et.isoformat(),
        timeframe=timeframe,
        watchlist=watchlist,
        successful_scans=successful,
        failed_scans=failed,
        market_posture=posture,
        average_score=average_score,
        strongest_tickers=ranked_symbols(
            ticker_reports,
            reverse=True,
        ),
        weakest_tickers=ranked_symbols(
            ticker_reports,
            reverse=False,
        ),
        ticker_reports=ticker_reports,
    )


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------

def format_value(value: object, fallback: str = "N/A") -> str:
    """Format report values consistently."""
    if value is None:
        return fallback

    return str(value)


def render_text_report(report: MorningReport) -> str:
    """Create terminal-friendly plain-text output."""
    line = "=" * 78
    section = "-" * 78

    output: list[str] = [
        line,
        "PATCC - PROFESSIONAL AI TRADING & CAPITAL COMPANION",
        "MORNING COMMAND CENTER",
        f"Version             : {report.report_version}",
        f"Generated           : {report.generated_at_et}",
        f"Timeframe           : {report.timeframe}",
        line,
        "",
        "EXECUTIVE SUMMARY",
        section,
        f"Market Posture       : {report.market_posture}",
        f"Average Score        : {format_value(report.average_score)}",
        f"Successful Scans     : {report.successful_scans}",
        f"Failed Scans         : {report.failed_scans}",
        (
            "Strongest Tickers   : "
            + (
                ", ".join(report.strongest_tickers)
                if report.strongest_tickers
                else "Not available"
            )
        ),
        (
            "Weakest Tickers     : "
            + (
                ", ".join(report.weakest_tickers)
                if report.weakest_tickers
                else "Not available"
            )
        ),
        "",
        "WATCHLIST SUMMARY",
        section,
        (
            f"{'Ticker':<12}"
            f"{'Status':<11}"
            f"{'Price':>12}"
            f"{'Score':>9}"
            f"{'Grade':>12}"
            f"{'Action':>22}"
        ),
        section,
    ]

    for item in report.ticker_reports:
        price_text = (
            f"{item.price:,.2f}"
            if item.price is not None
            else "N/A"
        )
        score_text = (
            str(item.score)
            if item.score is not None
            else "N/A"
        )

        output.append(
            f"{item.ticker:<12}"
            f"{item.status:<11}"
            f"{price_text:>12}"
            f"{score_text:>9}"
            f"{item.grade[:11]:>12}"
            f"{item.action[:21]:>22}"
        )

    output.extend(
        [
            "",
            "TICKER DRILL-DOWN",
            section,
        ]
    )

    for item in report.ticker_reports:
        output.extend(
            [
                "",
                f"{item.ticker} — {item.status}",
                "-" * 40,
                f"Timeframe            : {item.timeframe}",
                f"Price                : {format_value(item.price)}",
                f"Score                : {format_value(item.score)}",
                f"Grade                : {item.grade}",
                f"Action               : {item.action}",
                f"Trend                : {item.trend}",
                f"Market State         : {item.market_state}",
                f"Provider             : {item.provider}",
            ]
        )

        if item.error:
            output.append(f"Error                : {item.error}")

        output.extend(
            [
                "",
                "SCORING ENGINE OUTPUT",
                "-" * 40,
                item.raw_output or "No output returned.",
            ]
        )

    output.extend(
        [
            "",
            line,
            "PATCC v0.1 is decision support, not a guarantee of market outcomes.",
            line,
        ]
    )

    return "\n".join(output)


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def score_class(score: int | None) -> str:
    """Return a CSS class based on score."""
    if score is None:
        return "score-na"
    if score >= 80:
        return "score-strong"
    if score >= 65:
        return "score-positive"
    if score >= 50:
        return "score-neutral"
    if score >= 35:
        return "score-caution"
    return "score-risk"


def status_badge(status: str) -> str:
    """Create a status badge."""
    css_class = "success" if status == "SUCCESS" else "failed"
    return (
        f'<span class="badge {css_class}">'
        f"{html.escape(status)}"
        f"</span>"
    )


def render_ticker_card(item: TickerReport) -> str:
    """Create one expandable ticker drill-down card."""
    price_text = (
        f"${item.price:,.2f}"
        if item.price is not None
        else "N/A"
    )
    score_text = (
        str(item.score)
        if item.score is not None
        else "N/A"
    )

    error_html = ""

    if item.error:
        error_html = (
            '<div class="alert-error">'
            f"<strong>Error:</strong> {html.escape(item.error)}"
            "</div>"
        )

    return f"""
    <details class="ticker-card">
        <summary>
            <div class="ticker-summary">
                <div>
                    <span class="ticker-symbol">{html.escape(item.ticker)}</span>
                    {status_badge(item.status)}
                </div>
                <div class="ticker-metrics">
                    <span>Price: <strong>{price_text}</strong></span>
                    <span>
                        Score:
                        <strong class="{score_class(item.score)}">
                            {score_text}
                        </strong>
                    </span>
                    <span>Action: <strong>{html.escape(item.action)}</strong></span>
                </div>
            </div>
        </summary>

        <div class="ticker-details">
            <div class="detail-grid">
                <div class="detail-item">
                    <span>Timeframe</span>
                    <strong>{html.escape(item.timeframe)}</strong>
                </div>

                <div class="detail-item">
                    <span>Grade</span>
                    <strong>{html.escape(item.grade)}</strong>
                </div>

                <div class="detail-item">
                    <span>Trend</span>
                    <strong>{html.escape(item.trend)}</strong>
                </div>

                <div class="detail-item">
                    <span>Market State</span>
                    <strong>{html.escape(item.market_state)}</strong>
                </div>

                <div class="detail-item">
                    <span>Provider</span>
                    <strong>{html.escape(item.provider)}</strong>
                </div>

                <div class="detail-item">
                    <span>Status</span>
                    <strong>{html.escape(item.status)}</strong>
                </div>
            </div>

            {error_html}

            <h3>Full PATCC Scoring Output</h3>
            <pre>{html.escape(item.raw_output or "No output returned.")}</pre>
        </div>
    </details>
    """


def render_html_report(report: MorningReport) -> str:
    """Create the browser-accessible PATCC Command Center."""
    average_score = (
        str(report.average_score)
        if report.average_score is not None
        else "N/A"
    )

    strongest = (
        ", ".join(report.strongest_tickers)
        if report.strongest_tickers
        else "Not available"
    )

    weakest = (
        ", ".join(report.weakest_tickers)
        if report.weakest_tickers
        else "Not available"
    )

    table_rows: list[str] = []

    for item in report.ticker_reports:
        price_text = (
            f"${item.price:,.2f}"
            if item.price is not None
            else "N/A"
        )
        score_text = (
            str(item.score)
            if item.score is not None
            else "N/A"
        )

        table_rows.append(
            f"""
            <tr>
                <td><strong>{html.escape(item.ticker)}</strong></td>
                <td>{status_badge(item.status)}</td>
                <td>{price_text}</td>
                <td class="{score_class(item.score)}">
                    <strong>{score_text}</strong>
                </td>
                <td>{html.escape(item.grade)}</td>
                <td>{html.escape(item.trend)}</td>
                <td>{html.escape(item.action)}</td>
            </tr>
            """
        )

    ticker_cards = "\n".join(
        render_ticker_card(item)
        for item in report.ticker_reports
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
    <title>PATCC Morning Command Center</title>

    <style>
        :root {{
            --background: #0b1220;
            --panel: #121c2e;
            --panel-light: #18243a;
            --border: #2a3952;
            --text: #eef4ff;
            --muted: #9fb0c8;
            --accent: #55b8ff;
            --success: #2bd576;
            --warning: #ffca58;
            --danger: #ff6b6b;
            --neutral: #9fb0c8;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background:
                radial-gradient(circle at top right, #162a46, var(--background));
            color: var(--text);
            font-family:
                Inter,
                Segoe UI,
                Arial,
                sans-serif;
            line-height: 1.5;
        }}

        .container {{
            width: min(1440px, 96%);
            margin: 0 auto;
            padding: 24px 0 60px;
        }}

        .header {{
            padding: 26px;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: rgba(18, 28, 46, 0.95);
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.24);
        }}

        .eyebrow {{
            color: var(--accent);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }}

        h1 {{
            margin: 8px 0 2px;
            font-size: clamp(1.7rem, 4vw, 2.8rem);
        }}

        .subtitle {{
            color: var(--muted);
            margin: 0;
        }}

        .posture {{
            margin-top: 18px;
            padding: 15px 18px;
            border-left: 5px solid var(--accent);
            border-radius: 8px;
            background: var(--panel-light);
            font-weight: 700;
        }}

        .dashboard-grid {{
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(190px, 1fr));
            gap: 14px;
            margin-top: 20px;
        }}

        .metric-card {{
            min-height: 118px;
            padding: 18px;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: var(--panel);
        }}

        .metric-card span {{
            display: block;
            color: var(--muted);
            font-size: 0.87rem;
            margin-bottom: 8px;
        }}

        .metric-card strong {{
            display: block;
            font-size: 1.22rem;
        }}

        .section {{
            margin-top: 24px;
            padding: 22px;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: rgba(18, 28, 46, 0.96);
        }}

        .section h2 {{
            margin-top: 0;
            margin-bottom: 16px;
            font-size: 1.35rem;
        }}

        .table-wrap {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 850px;
        }}

        th,
        td {{
            padding: 13px 12px;
            border-bottom: 1px solid var(--border);
            text-align: left;
        }}

        th {{
            color: var(--muted);
            font-size: 0.78rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        tbody tr:hover {{
            background: var(--panel-light);
        }}

        .badge {{
            display: inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.04em;
        }}

        .badge.success {{
            color: #07170d;
            background: var(--success);
        }}

        .badge.failed {{
            color: #210707;
            background: var(--danger);
        }}

        .score-strong {{
            color: var(--success);
        }}

        .score-positive {{
            color: #80e49f;
        }}

        .score-neutral,
        .score-na {{
            color: var(--neutral);
        }}

        .score-caution {{
            color: var(--warning);
        }}

        .score-risk {{
            color: var(--danger);
        }}

        .ticker-card {{
            margin-top: 12px;
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            background: var(--panel-light);
        }}

        .ticker-card summary {{
            cursor: pointer;
            padding: 17px;
            list-style: none;
        }}

        .ticker-card summary::-webkit-details-marker {{
            display: none;
        }}

        .ticker-summary {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 18px;
        }}

        .ticker-symbol {{
            margin-right: 10px;
            font-size: 1.18rem;
            font-weight: 800;
        }}

        .ticker-metrics {{
            display: flex;
            flex-wrap: wrap;
            gap: 18px;
            color: var(--muted);
            font-size: 0.9rem;
        }}

        .ticker-details {{
            padding: 0 17px 20px;
            border-top: 1px solid var(--border);
        }}

        .detail-grid {{
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            padding: 18px 0;
        }}

        .detail-item {{
            padding: 12px;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: var(--panel);
        }}

        .detail-item span {{
            display: block;
            color: var(--muted);
            font-size: 0.78rem;
            margin-bottom: 5px;
        }}

        pre {{
            max-height: 620px;
            overflow: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            padding: 18px;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: #080e18;
            color: #dbe7f7;
            font-family:
                Consolas,
                "Courier New",
                monospace;
            font-size: 0.86rem;
        }}

        .alert-error {{
            margin: 12px 0;
            padding: 13px;
            border-left: 4px solid var(--danger);
            border-radius: 7px;
            background: rgba(255, 107, 107, 0.13);
        }}

        .footer {{
            margin-top: 24px;
            color: var(--muted);
            font-size: 0.83rem;
            text-align: center;
        }}

        @media (max-width: 720px) {{
            .container {{
                width: 94%;
            }}

            .header,
            .section {{
                padding: 17px;
            }}

            .ticker-summary {{
                align-items: flex-start;
                flex-direction: column;
            }}

            .ticker-metrics {{
                flex-direction: column;
                gap: 7px;
            }}
        }}
    </style>
</head>

<body>
    <main class="container">
        <header class="header">
            <div class="eyebrow">
                Professional AI Trading & Capital Companion
            </div>

            <h1>PATCC Morning Command Center</h1>

            <p class="subtitle">
                Version {html.escape(report.report_version)}
                &nbsp;•&nbsp;
                {html.escape(report.generated_at_et)}
                &nbsp;•&nbsp;
                Timeframe {html.escape(report.timeframe)}
            </p>

            <div class="posture">
                Market Posture:
                {html.escape(report.market_posture)}
            </div>

            <div class="dashboard-grid">
                <div class="metric-card">
                    <span>Average PATCC Score</span>
                    <strong>{average_score}</strong>
                </div>

                <div class="metric-card">
                    <span>Successful Scans</span>
                    <strong>{report.successful_scans}</strong>
                </div>

                <div class="metric-card">
                    <span>Failed Scans</span>
                    <strong>{report.failed_scans}</strong>
                </div>

                <div class="metric-card">
                    <span>Strongest Tickers</span>
                    <strong>{html.escape(strongest)}</strong>
                </div>

                <div class="metric-card">
                    <span>Weakest Tickers</span>
                    <strong>{html.escape(weakest)}</strong>
                </div>
            </div>
        </header>

        <section class="section">
            <h2>Watchlist Summary</h2>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th>Status</th>
                            <th>Price</th>
                            <th>Score</th>
                            <th>Grade</th>
                            <th>Trend</th>
                            <th>Action</th>
                        </tr>
                    </thead>

                    <tbody>
                        {''.join(table_rows)}
                    </tbody>
                </table>
            </div>
        </section>

        <section class="section">
            <h2>Ticker Drill-Down</h2>

            <p class="subtitle">
                Select any ticker to view the complete PATCC scoring output.
            </p>

            {ticker_cards}
        </section>

        <footer class="footer">
            PATCC is a decision-support system. Market outcomes are uncertain,
            and every position requires independent risk controls.
        </footer>
    </main>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------

def write_report_files(
    report: MorningReport,
) -> tuple[Path, Path, Path]:
    """Write JSON, text, and HTML reports to latest and archive folders."""
    ensure_directories()

    now_et = datetime.now(EASTERN_TIME)
    archive_folder = (
        ARCHIVE_DIR
        / now_et.strftime("%Y-%m-%d")
        / now_et.strftime("%H%M%S")
    )
    archive_folder.mkdir(parents=True, exist_ok=True)
    monthly_folder = MONTHLY_DIR / now_et.strftime("%Y-%m")
    monthly_folder.mkdir(parents=True, exist_ok=True)

    json_content = json.dumps(
        asdict(report),
        indent=2,
        ensure_ascii=False,
    )
    text_content = render_text_report(report)
    html_content = render_html_report(report)

    latest_json = LATEST_DIR / "morning_report.json"
    latest_text = LATEST_DIR / "morning_report.txt"
    latest_html = LATEST_DIR / "morning_report.html"

    archive_json = archive_folder / "morning_report.json"
    archive_text = archive_folder / "morning_report.txt"
    archive_html = archive_folder / "morning_report.html"
    
    monthly_json = monthly_folder / "morning_report.json"
    monthly_text = monthly_folder / "morning_report.txt"
    monthly_html = monthly_folder / "morning_report.html"

    latest_json.write_text(json_content, encoding="utf-8")
    latest_text.write_text(text_content, encoding="utf-8")
    latest_html.write_text(html_content, encoding="utf-8")

    archive_json.write_text(json_content, encoding="utf-8")
    archive_text.write_text(text_content, encoding="utf-8")
    archive_html.write_text(html_content, encoding="utf-8")

    # The newest report generated during the month becomes that month's
    # preserved research snapshot.
    monthly_json.write_text(json_content, encoding="utf-8")
    monthly_text.write_text(text_content, encoding="utf-8")
    monthly_html.write_text(html_content, encoding="utf-8")

    return latest_text, latest_html, latest_json


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate the PATCC Morning Command Center "
            "from the existing scoring engine."
        )
    )

    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_WATCHLIST,
        help=(
            "Ticker symbols to scan. "
            "Example: --tickers SPY QQQ IWM UNG"
        ),
    )

    parser.add_argument(
        "--tf",
        default="1d",
        help="Scoring-engine timeframe. Default: 1d",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Maximum seconds allowed per ticker. Default: 120",
    )

    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated HTML report in the default browser.",
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help=(
            "Run report cleanup. When used by itself, cleanup runs "
            "without generating a new report."
        ),
    )

    parser.add_argument(
        "--cleanup-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=(
            "Number of days to retain detailed archive reports. "
            f"Default: {DEFAULT_RETENTION_DAYS}"
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Preview cleanup actions without deleting files. "
            "Use together with --cleanup."
        ),
    )

    return parser.parse_args()


def main() -> int:
    """Generate the PATCC Morning Command Center."""
    args = parse_arguments()

    if args.cleanup_days < 1:
        print("ERROR: --cleanup-days must be at least 1.")
        return 2

    if args.cleanup:
        print("=" * 78)
        print("PATCC REPORT CLEANUP")
        print("=" * 78)
        print(f"Archive retention : {args.cleanup_days} days")
        print(f"Error retention   : {ERROR_RETENTION_DAYS} days")
        print(f"Dry run           : {args.dry_run}")
        print("-" * 78)

        cleanup_actions = run_report_cleanup(
            archive_retention_days=args.cleanup_days,
            dry_run=args.dry_run,
        )

        for action in cleanup_actions:
            print(action)

        print("=" * 78)

        # A cleanup-only command should stop after cleanup.
        if not args.open:
            return 0

    watchlist = normalize_tickers(args.tickers)


    if not watchlist:
        print("ERROR: No valid ticker symbols were supplied.")
        return 2

    print("=" * 78)
    print("PATCC MORNING COMMAND CENTER v0.1")
    print("=" * 78)
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Timeframe    : {args.tf}")
    print(f"Watchlist    : {', '.join(watchlist)}")
    print("-" * 78)

    ticker_reports: list[TickerReport] = []

    for position, ticker in enumerate(watchlist, start=1):
        print(
            f"[{position}/{len(watchlist)}] "
            f"Scanning {ticker}...",
            end="",
            flush=True,
        )

        result = run_scoring_engine(
            ticker=ticker,
            timeframe=args.tf,
            timeout_seconds=args.timeout,
        )

        ticker_reports.append(result)

        if result.status == "SUCCESS":
            score_text = (
                str(result.score)
                if result.score is not None
                else "N/A"
            )
            print(
                f" SUCCESS | Score={score_text} "
                f"| Action={result.action}"
            )
        else:
            print(f" FAILED | {result.error}")

    report = build_report(
        ticker_reports=ticker_reports,
        timeframe=args.tf,
        watchlist=watchlist,
    )

    text_path, html_path, json_path = write_report_files(report)
        
    cleanup_actions = run_report_cleanup(
        archive_retention_days=args.cleanup_days,
        dry_run=False,
    )

    print("-" * 78)
    print(f"Text report : {text_path}")
    print(f"HTML report : {html_path}")
    print(f"JSON data   : {json_path}")
    print(f"Posture     : {report.market_posture}")
    print("Cleanup     : Automatic retention cleanup completed")

    for action in cleanup_actions:
        print(f"              {action}")
    print("=" * 78)

    if args.open:
        webbrowser.open(html_path.resolve().as_uri())

    return 0 if report.successful_scans > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
