from Core.market_state import MarketStateEngine


def main():
    engine = MarketStateEngine()
    state = engine.analyze_market()

    print("\nSummary")
    print("-------")
    print(f"Market Bias : {state.market_bias}")
    print(f"Trend       : {state.trend}")
    print(f"Risk Level  : {state.risk_level}")


if __name__ == "__main__":
    main()
