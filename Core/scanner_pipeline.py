"""
scanner_pipeline.py

End-to-end scanner pipeline with command-line support.
"""

import argparse
from dataclasses import dataclass
from typing import List

from asset_classifier import AssetClassifier
from indicator_engine import IndicatorEngine
from market_data_service import MarketDataRequest, MarketDataService
from market_state_analyzer import MarketStateAnalyzer
from scoring_engine import ScoringEngine
from universe_manager import UniverseManager


@dataclass
class ScanResult:
    ticker: str
    asset_type: str
    market_response: object
    market_state: object
    score: object


class ScannerPipeline:
    """Coordinates the complete analysis workflow."""

    def __init__(self):
        self.classifier = AssetClassifier()
        self.market_data = MarketDataService()
        self.indicator_engine = IndicatorEngine()
        self.market_state = MarketStateAnalyzer()
        self.scoring = ScoringEngine()

    def analyze(self, ticker: str, period: str = "1y", interval: str = "1d") -> ScanResult:
        asset_type = self.classifier.classify(ticker)

        market_response = self.market_data.get_price_history(
            MarketDataRequest(ticker=ticker, period=period, interval=interval)
        )

        indicators = self.indicator_engine.calculate(market_response.data)

        state = self.market_state.analyze(indicators)

        score = self.scoring.score(
            indicators=indicators,
            state=state,
            profile=asset_type,
        )

        return ScanResult(
            ticker=ticker.upper(),
            asset_type=asset_type,
            market_response=market_response,
            market_state=state,
            score=score,
        )


def print_report(result: ScanResult):
    print("=" * 60)
    print(f"Ticker      : {result.ticker}")
    print(f"Asset Type  : {result.asset_type}")
    print(f"Data Source : {result.market_response.source}")
    print(f"Data Mode   : {result.market_response.mode}")
    print(f"Real-Time   : {result.market_response.realtime}")
    print(f"Last Bar    : {result.market_response.last_bar.date()}")
    print("-" * 60)
    print(f"Trend       : {result.market_state.trend}")
    print(f"Momentum    : {result.market_state.momentum}")
    print(f"Volatility  : {result.market_state.volatility}")
    print(f"Volume      : {result.market_state.volume}")
    print(f"Bias        : {result.market_state.market_bias}")
    print(f"Risk        : {result.market_state.risk_level}")
    print("-" * 60)
    print(f"Overall     : {result.score.overall_score}/100")
    print(f"Grade       : {result.score.grade}")
    print(f"Action      : {result.score.action}")
    print("-" * 60)
    print("Component Scores")
    print(f"Trend       : {result.score.trend_score}")
    print(f"Momentum    : {result.score.momentum_score}")
    print(f"Volume      : {result.score.volume_score}")
    print(f"Volatility  : {result.score.volatility_score}")
    print(f"Risk        : {result.score.risk_score}")
    print("=" * 60)


def print_ranking(results: List[ScanResult]):
    ranked = sorted(results, key=lambda r: r.score.overall_score, reverse=True)

    print("\nRANKED RESULTS")
    print("=" * 80)
    print(f"{'Rank':<6}{'Ticker':<10}{'Type':<18}{'Score':<8}{'Grade':<8}{'Action'}")
    print("-" * 80)

    for index, result in enumerate(ranked, start=1):
        print(
            f"{index:<6}"
            f"{result.ticker:<10}"
            f"{result.asset_type:<18}"
            f"{result.score.overall_score:<8}"
            f"{result.score.grade:<8}"
            f"{result.score.action}"
        )

    print("=" * 80)


def parse_tickers(args) -> List[str]:
    if args.ticker:
        return [args.ticker.upper().strip()]

    if args.tickers:
        return [
            ticker.strip().upper()
            for ticker in args.tickers.split(",")
            if ticker.strip()
        ]

    if args.universe:
        manager = UniverseManager()
        return manager.load(args.universe)

    return ["AAPL", "SPY", "TQQQ", "SOXL", "NVDL"]


def main():
    parser = argparse.ArgumentParser(description="AI Trading Scanner Pipeline")

    parser.add_argument("--ticker", help="Analyze one ticker, example: MSTX")
    parser.add_argument("--tickers", help="Analyze comma-separated tickers, example: MSTX,MSTU,SPCH,LOFF")
    parser.add_argument("--universe", help="Analyze a saved universe, example: leveraged")
    parser.add_argument("--period", default="1y", help="Data period, default: 1y")
    parser.add_argument("--interval", default="1d", help="Data interval, default: 1d")
    parser.add_argument("--details", action="store_true", help="Print detailed report for each ticker")

    args = parser.parse_args()

    tickers = parse_tickers(args)
    pipeline = ScannerPipeline()

    results = []

    for ticker in tickers:
        try:
            result = pipeline.analyze(
                ticker=ticker,
                period=args.period,
                interval=args.interval,
            )
            results.append(result)

            if args.details:
                print_report(result)

        except Exception as ex:
            print(f"{ticker}: ERROR - {ex}")

    if results:
        print_ranking(results)


if __name__ == "__main__":
    main()
    