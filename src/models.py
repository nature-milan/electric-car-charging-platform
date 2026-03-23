from dataclasses import dataclass
from datetime import datetime


@dataclass
class DemoAdminState:
    car_is_plugged_in: bool
    current_time: datetime


@dataclass
class ChargerState:
    car_is_charging: bool
    charge_is_override: bool


@dataclass
class CombinedState:
    soc: float
    time: datetime
    charger_state: ChargerState


@dataclass
class BackendState:
    soc: float
    override_until: datetime | None
    schedule_disabled_until: datetime | None


@dataclass(frozen=True)
class ChargeSpan:
    start: datetime
    end: datetime
    is_override: bool


@dataclass(frozen=True)
class WindowSpan:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class ManualChargeEvent:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class SchedulePauseEvent:
    start: datetime
    end: datetime
