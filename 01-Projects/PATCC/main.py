from Core.market_state import MarketStateEngine
from Core.universe_manager import UniverseManager

from Utils.formatting import print_header


def main():

    print_header("PATCC Trading Platform")

    market = MarketStateEngine()

    state = market.analyze_market()

    print("\nMarket Summary")
    print("--------------")
    print(f"Bias : {state.market_bias}")
    print(f"Trend: {state.trend}")
    print(f"Risk : {state.risk_level}")

    manager = UniverseManager()

    print("\nAvailable Universes")
    print("-------------------")

    for name in manager.get_universe_names():
        print(name)


if __name__ == "__main__":
    main()
