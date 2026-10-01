from pydantic import BaseModel, ConfigDict
from typing import List, Dict
from enum import Enum

class TimeWindow(str, Enum):
    WINDOW_24H = "24h"
    WINDOW_7D = "7d"
    WINDOW_30D = "30d"

class TrendPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    timestamp: str
    count: int

class EventAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_events: int
    by_type: Dict[str, int]
    by_outcome: Dict[str, int]
    trend: List[TrendPoint]

class IncidentAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_incidents: int
    open_incidents: int
    by_severity: Dict[str, int]
    trend: List[TrendPoint]

class AlertAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_alerts: int
    by_status: Dict[str, int]
    trend: List[TrendPoint]

class EvidenceAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_evidence: int

class InvestigationAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_investigations: int
    by_status: Dict[str, int]
    trend: List[TrendPoint]

class ExecutionAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_decisions: int
    by_effect: Dict[str, int]
    trend: List[TrendPoint]
