from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Action:
    """
    Structured action object produced by CommandParser.

    type   : loại action chính
    target : đối tượng target (grid cell / direction / text ...)
    params : metadata mở rộng
    """

    type: str
    target: Optional[Any] = None
    params: Dict[str, Any] = field(default_factory=dict)