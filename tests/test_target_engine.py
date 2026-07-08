import pandas as pd

from Core.target_engine import TargetEngine, TargetLevels


def test_target_engine_calculates_levels():
    df = pd.DataFrame(
        {
            "High": [100, 105, 110, 115, 120],
            "Low": [90, 92, 95, 98, 100],
            "Close": [95, 100, 108, 112, 118],
        }
    )

    engine = TargetEngine()
    result = engine.calculate(df)

    assert isinstance(result, TargetLevels)
    assert result.support == 90
    assert result.resistance == 120
    assert result.target_1 > 118
    assert result.target_2 > result.target_1
    assert result.target_3 > result.target_2
    assert result.stop_loss < result.support
    assert result.risk_reward_1 >= 0
    