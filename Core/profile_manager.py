"""
profile_manager.py

Loads and validates PATCC trading profiles.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import yaml


@dataclass
class TradingProfile:
    name: str
    mode: str
    market_type: str
    period: str
    interval: str
    profile: str
    atr_period: int
    target_model: str
    risk_model: str
    report_style: str


class ProfileManager:
    """
    Central configuration manager for PATCC trading profiles.
    """

    PROFILE_DIR = Path("Config/profiles")

    def load(self, profile_name: str = "swing") -> TradingProfile:
        profile_name = profile_name.lower().strip()
        profile_path = self.PROFILE_DIR / f"{profile_name}.yaml"

        if not profile_path.exists():
            raise FileNotFoundError(f"Profile not found: {profile_path}")

        with open(profile_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        self._validate(profile_name, data)

        return TradingProfile(
            name=data["name"],
            mode=data["mode"],
            market_type=data["market_type"],
            period=data["period"],
            interval=data["interval"],
            profile=data["profile"],
            atr_period=int(data["atr_period"]),
            target_model=data["target_model"],
            risk_model=data["risk_model"],
            report_style=data["report_style"],
        )

    def _validate(self, profile_name: str, data: Dict[str, Any]) -> None:
        required = [
            "name",
            "mode",
            "market_type",
            "period",
            "interval",
            "profile",
            "atr_period",
            "target_model",
            "risk_model",
            "report_style",
        ]

        missing = [field for field in required if field not in data]

        if missing:
            raise ValueError(f"Profile {profile_name} missing fields: {missing}")


if __name__ == "__main__":
    manager = ProfileManager()

    for profile_name in ["swing", "intraday", "entry"]:
        profile = manager.load(profile_name)

        print("=" * 60)
        print(f"Profile      : {profile.name}")
        print(f"Mode         : {profile.mode}")
        print(f"Period       : {profile.period}")
        print(f"Interval     : {profile.interval}")
        print(f"Risk Model   : {profile.risk_model}")
        print(f"Target Model : {profile.target_model}")
        