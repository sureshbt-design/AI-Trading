from Core.analysis_result import AnalysisResult


def test_analysis_result_holds_complete_ticker_analysis():
    result = AnalysisResult(
        ticker="TQQQ",
        profile="leveraged_etf",
        market_data={"source": "mock"},
        indicators={"rsi": 60},
        market_state={"trend": "Bullish"},
        score={"overall_score": 80},
        targets={"target_1": 100},
    )

    assert result.ticker == "TQQQ"
    assert result.profile == "leveraged_etf"
    assert result.market_data["source"] == "mock"
    assert result.indicators["rsi"] == 60
    assert result.market_state["trend"] == "Bullish"
    assert result.score["overall_score"] == 80
    assert result.targets["target_1"] == 100
    