from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time


@dataclass
class SensorConfig:
    name: str
    port: str
    address: int
    baudrate: int
    profile: str
    simulated: bool = False
    timeout: float = 1.5


@dataclass
class ConnectedSensor:
    config: SensorConfig
    sensor: Any
    profile_data: Dict[str, Any]
    connected_at: float = field(default_factory=time.time)
    last_error: Optional[str] = None
    status: str = "connected"
    consecutive_failures: int = 0
    last_ok_at: float = field(default_factory=time.time)
    last_reconnect_at: float = 0.0
