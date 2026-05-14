from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class SiteProfile:
    site_id: str
    site_type: str
    capacity_multiplier: float
    utilization_base: float
    climate_multiplier: float


SITE_CAPACITY_RANGES = {
    "plant": (5.0, 20.0),
    "r_and_d": (1.0, 4.0),
    "warehouse": (0.5, 2.0),
    "office": (0.1, 0.8),
}

SITE_UTILIZATION_RANGES = {
    "plant": (0.68, 0.93),
    "r_and_d": (0.45, 0.75),
    "warehouse": (0.35, 0.65),
    "office": (0.25, 0.55),
}

ACTIVITY_BASE = {
    "electricity": 95_000.0,
    "diesel": 2_500.0,
    "natural_gas": 18_000.0,
    "steam": 550.0,
}

ACTIVITY_WEIGHTS_BY_SITE_TYPE = {
    "plant": {"electricity": 0.64, "natural_gas": 0.18, "steam": 0.13, "diesel": 0.05},
    "r_and_d": {"electricity": 0.72, "natural_gas": 0.12, "steam": 0.04, "diesel": 0.12},
    "warehouse": {"electricity": 0.76, "natural_gas": 0.06, "steam": 0.01, "diesel": 0.17},
    "office": {"electricity": 0.88, "natural_gas": 0.04, "steam": 0.00, "diesel": 0.08},
}

LINE_INTENSITY = {
    "electrode_coating_line": 1.35,
    "cell_assembly_line": 1.10,
    "formation_line": 1.65,
    "aging_line": 1.20,
    "module_pack_line": 0.85,
}


def build_site_profiles(sites: list[dict[str, Any]], rng: random.Random) -> dict[str, SiteProfile]:
    profiles: dict[str, SiteProfile] = {}
    for site in sites:
        site_type = str(site.get("site_type", "plant"))
        cap_low, cap_high = SITE_CAPACITY_RANGES.get(site_type, (1.0, 3.0))
        util_low, util_high = SITE_UTILIZATION_RANGES.get(site_type, (0.4, 0.8))
        profiles[str(site["site_id"])] = SiteProfile(
            site_id=str(site["site_id"]),
            site_type=site_type,
            capacity_multiplier=round(rng.uniform(cap_low, cap_high), 4),
            utilization_base=round(rng.uniform(util_low, util_high), 4),
            climate_multiplier=round(rng.uniform(0.94, 1.08), 4),
        )
    return profiles


def choose_activity_for_site(site_type: str, rng: random.Random) -> str:
    weights = ACTIVITY_WEIGHTS_BY_SITE_TYPE.get(site_type, ACTIVITY_WEIGHTS_BY_SITE_TYPE["plant"])
    activity_types = list(weights)
    values = list(weights.values())
    return rng.choices(activity_types, weights=values, k=1)[0]


def monthly_activity_amount(
    *,
    activity_type: str,
    site_profile: SiteProfile,
    month_number: int,
    rng: random.Random,
    line_type: str | None = None,
    previous_amount: float | None = None,
) -> float:
    seasonal = seasonal_factor(activity_type, month_number) * site_profile.climate_multiplier
    capacity = site_profile.capacity_multiplier
    utilization = max(0.05, min(1.25, rng.gauss(site_profile.utilization_base, 0.08)))
    line_factor = LINE_INTENSITY.get(line_type or "", 1.0)
    base = ACTIVITY_BASE.get(activity_type, 10_000.0)

    if activity_type == "electricity":
        amount = base * capacity * utilization * line_factor * seasonal * rng.lognormvariate(0.0, 0.22)
    elif activity_type == "diesel":
        if rng.random() < diesel_zero_probability(site_profile.site_type):
            amount = rng.uniform(0.0, base * 0.08)
        else:
            amount = base * max(0.1, capacity * 0.22) * rng.gammavariate(2.0, 0.55)
            if rng.random() < 0.04:
                amount *= rng.uniform(3.0, 8.0)
    elif activity_type == "natural_gas":
        site_factor = 1.0 if site_profile.site_type in ("plant", "r_and_d") else 0.18
        amount = base * capacity * site_factor * seasonal * rng.lognormvariate(0.0, 0.28)
    elif activity_type == "steam":
        if site_profile.site_type != "plant" and rng.random() < 0.75:
            amount = rng.uniform(0.0, base * 0.03)
        else:
            amount = base * capacity * line_factor * seasonal * rng.lognormvariate(0.0, 0.30)
    else:
        amount = base * capacity * seasonal * rng.lognormvariate(0.0, 0.25)

    if previous_amount is not None:
        amount = previous_amount * 0.68 + amount * 0.32
        if rng.random() < 0.025:
            amount *= rng.uniform(0.65, 1.45)

    return round(max(0.0, amount), 6)


def seasonal_factor(activity_type: str, month_number: int) -> float:
    angle = (month_number / 12.0) * 2.0 * math.pi
    if activity_type == "electricity":
        return 1.0 + 0.10 * math.sin(angle - math.pi / 8)
    if activity_type == "natural_gas":
        return 1.0 + 0.16 * math.cos(angle)
    if activity_type == "steam":
        return 1.0 + 0.12 * math.cos(angle)
    return 1.0 + 0.04 * math.sin(angle)


def diesel_zero_probability(site_type: str) -> float:
    return {
        "plant": 0.18,
        "r_and_d": 0.38,
        "warehouse": 0.30,
        "office": 0.62,
    }.get(site_type, 0.30)


def split_monthly_amount(total: float, parts: int, rng: random.Random) -> list[float]:
    if parts < 1:
        raise ValueError("parts must be >= 1")
    if total <= 0:
        return [0.0 for _ in range(parts)]
    weights = [rng.gammavariate(2.0, 1.0) for _ in range(parts)]
    weight_sum = sum(weights) or 1.0
    readings = [round(total * weight / weight_sum, 6) for weight in weights]
    readings[-1] = round(total - sum(readings[:-1]), 6)
    return readings


def distribution_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    by_activity: dict[str, list[float]] = {}
    for row in rows:
        activity_type = str(row.get("activity_type", "unknown"))
        try:
            amount = float(row.get("standardized_amount", 0.0))
        except (TypeError, ValueError):
            continue
        by_activity.setdefault(activity_type, []).append(amount)
    return {activity: summarize(values) for activity, values in sorted(by_activity.items())}


def summarize(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "min": 0, "mean": 0, "p50": 0, "p95": 0, "p99": 0, "max": 0}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min": round(ordered[0], 6),
        "mean": round(mean(ordered), 6),
        "p50": round(percentile(ordered, 0.50), 6),
        "p95": round(percentile(ordered, 0.95), 6),
        "p99": round(percentile(ordered, 0.99), 6),
        "max": round(ordered[-1], 6),
    }


def percentile(ordered_values: list[float], p: float) -> float:
    if not ordered_values:
        return 0.0
    if len(ordered_values) == 1:
        return ordered_values[0]
    position = (len(ordered_values) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered_values[int(position)]
    fraction = position - lower
    return ordered_values[lower] * (1 - fraction) + ordered_values[upper] * fraction
