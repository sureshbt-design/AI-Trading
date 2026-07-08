from types import SimpleNamespace

from Core.alert_engine import AlertEngine


def test_alert_engine_detects_events():

    indicators = SimpleNamespace(
        rsi14=75,
        rvol=2.5,
        atr_percent=9,
    )

    engine = AlertEngine()

    alerts = engine.analyze(indicators)

    assert len(alerts) == 3
    