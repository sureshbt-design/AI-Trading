"""
report_builder.py

Creates formatted reports from AnalysisResult.
"""

from Core.analysis_result import AnalysisResult


class ReportBuilder:

    def build_console_report(self, result: AnalysisResult) -> str:

        lines = []

        lines.append("=" * 65)
        lines.append("PATCC - Professional AI Trading & Capital Companion")
        lines.append("=" * 65)

        lines.append(f"Ticker              : {result.ticker}")
        lines.append(f"Profile             : {result.profile}")

        lines.append("")
        lines.append("MARKET STATE")
        lines.append("-" * 65)

        lines.append(f"Trend               : {result.market_state.trend}")
        lines.append(f"Momentum            : {result.market_state.momentum}")
        lines.append(f"Volatility          : {result.market_state.volatility}")
        lines.append(f"Volume              : {result.market_state.volume}")
        lines.append(f"Market Bias         : {result.market_state.market_bias}")
        lines.append(f"Risk Level          : {result.market_state.risk_level}")

        lines.append("")
        lines.append("SCORING")
        lines.append("-" * 65)

        lines.append(f"Overall Score       : {result.score.overall_score}")
        lines.append(f"Grade               : {result.score.grade}")
        lines.append(f"Recommendation      : {result.score.action}")

        lines.append("")
        lines.append("TARGETS")
        lines.append("-" * 65)

        lines.append(f"Support             : {result.targets.support:.2f}")
        lines.append(f"Resistance          : {result.targets.resistance:.2f}")

        lines.append(f"Target 1            : {result.targets.target_1:.2f}")
        lines.append(f"Target 2            : {result.targets.target_2:.2f}")
        lines.append(f"Target 3            : {result.targets.target_3:.2f}")

        lines.append(f"Stop Loss           : {result.targets.stop_loss:.2f}")

        lines.append("")

        return "\n".join(lines)
