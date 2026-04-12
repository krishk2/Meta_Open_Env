from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal


# ACTION MODEL
class Action(BaseModel):
    action_type: Literal[
        "interrogate",
        "analyze_evidence",
        "check_cctv",
        "search_police_records",
        "query_web_information",
        "visit_location",
        "request_additional_data",
        "search_past_cases",
        "conclude_case"
    ]
    target_id: Optional[str] = None
    parameters: Optional[Dict[str, str]] = None


# SUSPECT MODEL
class Suspect(BaseModel):
    id: str
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["unknown", "suspected", "cleared"]


# OBSERVATION MODEL
class Observation(BaseModel):
    case_id: str
    case_description: str

    initial_facts: List[str]
    discovered_clues: List[str]
    previous_case_history: List[str]

    suspects: List[Suspect]

    available_actions: List[Literal[
        "interrogate",
        "analyze_evidence",
        "check_cctv",
        "search_police_records",
        "query_web_information",
        "visit_location",
        "request_additional_data",
        "search_past_cases",
        "conclude_case"
    ]]

    time_remaining: int
    budget_remaining: int

    steps_taken: int
    max_steps: int

    done: bool = False
    reward: float = 0.0

    metadata: Optional[Dict] = None
    score: Optional[float] = None
    valid_targets: Optional[List[str]] = None