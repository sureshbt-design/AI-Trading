from types import SimpleNamespace

from Core.analysis_result import AnalysisResult
from Core.report_builder import ReportBuilder


def test_report_builder_returns_string():

    result = AnalysisResult(
        ticker="QQQ",
        profile="ETF",
        market_data=None,
        indicators=None,
        market_state=SimpleNamespace(
            trend="Bullish",
            momentum="Bullish",
            volatility="Low",
            volume="Above Average",
            market_bias="Buy",
            risk_level="Moderate",
        ),
        score=SimpleNamespace(
            overall_score=84,
            grade="A",
            action="Strong Candidate",
        ),
        targets=SimpleNamespace(
            support=500,
            resistance=550,
            target_1=560,
            target_2=580,
            target_3=600,
            stop_loss=490,
        ),
    )

    report = ReportBuilder().build_console_report(result)

    assert isinstance(report, str)
    assert "Ticker" in report
    assert "QQQ" in report
    assert "Overall Score" in report
    