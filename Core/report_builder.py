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
        lines.append("DATA VALIDATION")
        lines.append("-" * 65)

        lines.append(f"Provider            : {result.market_data.source}")
        lines.append(f"Mode                : {result.market_data.mode}")
        lines.append(f"Real-Time           : {result.market_data.realtime}")
        lines.append(f"Last Bar            : {result.market_data.last_bar}")
        lines.append(f"Rows Downloaded     : {result.market_data.rows}")


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

        lines.append(f"Current Price       : {result.targets.current_price:.2f}")
        lines.append(f"Support             : {result.targets.support:.2f}")
        lines.append(f"Resistance          : {result.targets.resistance:.2f}")

        lines.append(f"Target 1            : {result.targets.target_1:.2f}")
        lines.append(f"Target 2            : {result.targets.target_2:.2f}")
        lines.append(f"Target 3            : {result.targets.target_3:.2f}")

        lines.append(f"Stop Loss           : {result.targets.stop_loss:.2f}")
        lines.append("")
        lines.append(f"Risk/Reward T1      : {result.targets.risk_reward_1:.2f}")
        lines.append(f"Risk/Reward T2      : {result.targets.risk_reward_2:.2f}")
        lines.append(f"Risk/Reward T3      : {result.targets.risk_reward_3:.2f}")

        lines.append("")
        lines.append(f"Probability T1      : {result.targets.probability_1:.0f}%")
        lines.append(f"Probability T2      : {result.targets.probability_2:.0f}%")
        lines.append(f"Probability T3      : {result.targets.probability_3:.0f}%")

        lines.append("")

        return "\n".join(lines)
