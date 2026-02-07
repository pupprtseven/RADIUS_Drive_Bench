from __future__ import annotations

import re
from enum import Enum
from typing import Dict, List


_ENUM_PREFIX_RE = re.compile(
    r"^\s*(?:\(?\s*)?(?:\d+|[A-Za-z]|[IVXLCDM]+)\s*[\)\.\:\-]\s*",
    re.IGNORECASE,
)

TAXONOMY_TEXT = """    1. Fully Closed (Lane closed, not passable)
   - 1.1 Weather-caused Closure
     -- 1.1.1 Snow
     -- 1.1.2 Rain
     -- 1.1.3 Wind
     -- 1.1.4 Others
   - 1.2 Full Closure for Construction/Maintenance
     -- 1.2.1 Pavement Construction/Repair
     -- 1.2.2 Large-equipment Occupation
     -- 1.2.3 Others
   - 1.3 Major Traffic Accident Closure
     -- 1.3.1 Dangerous Goods Transport Vehicle Accident (Leak/Explosion Risk)
     -- 1.3.2 Multiple-vehicle Pile-up Leading to Full Closure
     -- 1.3.3 Others (e.g., fire or other incidents leading to full closure)
   - 1.4 Activity/Event Control Closure
     -- 1.4.1 General Event Activities (Sports events, parades; temporary closure; usually with official notice and barricades)
     -- 1.4.2 Political Activities (Traffic Police Control, etc.)
     -- 1.4.3 Others
   - 1.5 Natural Disaster/Geological Disaster Closure
     -- 1.5.1 Pavement Itself Damaged by Disaster
     -- 1.5.2 Pavement Surface Disaster Deposition
     -- 1.5.3 Foreign Objects (Engineering Vehicles, Fallen Objects, etc.)

2. Semi-Closed (Lane semi-closed, passable as appropriate)
   - 2.1 Static Obstacle Blockage
     -- 2.1.1 Foreign Objects (Engineering Vehicles (leaving half lane), Fallen Objects, etc.)
     -- 2.1.2 Pavement Itself (Settlement or Collapse Occupying Lane)
   - 2.2 Dynamic Traffic Participant Blockage
     -- 2.2.1 Animals
     -- 2.2.2 Low-speed Large Vehicles (Harvesters, Super-long Transporters, etc.)
     -- 2.2.3 Pedestrians
     -- 2.2.4 Non-motor Vehicles
   - 2.3 Temporary Signals
    -- 2.3.1 Manual Signal / Human Command
    -- 2.3.2 Temporary Signal Lights or Signs
  - 2.4 Special Objects
    -- 2.4.1 Special Groups of People
    -- 2.4.2 Priority for Special Vehicles
    -- 2.4.3 Others
   - 2.5 Partial Pavement Abnormality
     -- 2.5.1 Impassable (Collapse, etc.)
     -- 2.5.2 Not Recommended to Pass (Potholes, Temporary Bridges, etc.)
     -- 2.5.3 Passable (Small Puddles, etc.)

3. Surface Open but with Potential Obstacles (Lane surface is clear but there are hidden risks)
   - 3.1 Abnormal Deceleration or Gathering of Front Traffic Flow
     -- 3.1.1 All U-turning Ahead (many vehicles collectively U-turn; no confirmed collision; may cause congestion)
     -- 3.1.2 All Changing Lanes Ahead (many vehicles collectively change lanes; may cause congestion)
     -- 3.1.3 All Emergency Braking/Stopping Ahead (multiple vehicles brake and stop; no confirmed collision)
   - 3.2 Inconsistent Information
     -- 3.2.1 Conflict with External Information (Navigation shows clear but there are closure signs on site; OR on-site is clear but navigation shows closure)
   - 3.3 Abnormal Behavior of Other Vehicles
     -- 3.3.1 Front Vehicle Sudden Braking
     -- 3.3.2 Sudden Lane Changing (Front/Left/Right Vehicle)
     -- 3.3.3 Abnormal Information (Front/Left/Right Vehicle) (Vehicle loss of control, etc.)
     -- 3.3.4 Others
   - 3.4 Low Visibility Blurred Objects
     -- 3.4.1 Weak Light (Thick Fog, Night, etc.)
     -- 3.4.2 Backlight, Strong Reflection
   - 3.5 Road Edge Overflow Risk
     -- 3.5.1 Objects (Improperly Parked Vehicles, Materials, etc.)
     -- 3.5.2 People
"""

LT_ELE_CHOICES: List[str] = [
    "None of the above / No long-tail element",
    "Snowy terrain", "Ponding water", "Sand and dust", "Construction work",
    "Large-scale equipment", "Hazardous materials transport vehicle accident",
    "Large-scale accident", "Small-scale accident", "Event control",
    "Natural disaster", "Ground obstacle", "Falling objects from above",
    "Animals", "Pedestrians", "Low-speed heavy vehicles",
    "Command signals/temporary signs", "Special vehicles", "Non-motorized vehicle",
    "Road surface damage-Severe", "Road surface damage-Moderate",
    "Road surface damage-Light", "Abnormal traffic flow-U-turn",
    "Abnormal traffic flow-Lane change", "Abnormal traffic flow-Parking",
    "Information conflict",
    "Abnormal behavior of other vehicles-Sudden braking",
    "Abnormal behavior of other vehicles-Sudden lane change",
    "Abnormal behavior of other vehicles-Vehicle body abnormality",
    "Poor visibility",
]

ACC_FACTORS_GROUPS: List[List[str]] = [
    ["Vehicles ahead", "Non-motor vehicles ahead", "No vehicles ahead"],
    ["Does not affect own vehicle's passage", "Affects own vehicle's passage"],
    [
        "No lane-borrowing possibility temporarily",
        "Lane-borrowing possible",
        "No lane-borrowing possibility",
    ],
]

# Mapping of long-tail taxonomy codes to the acc_factors groups that materially
# influence the final post-decision choice. Keys use normalized level3 codes.
ACC_FACTOR_EFFECTIVENESS_GT: Dict[str, set[int]] = {
    "1.1.1": {1, 2, 3}, "1.1.2": {1, 2, 3}, "1.1.3": {1, 2},
    "1.2.1": {2, 3}, "1.2.2": {2, 3},
    "1.3.1": set(), "1.3.2": {3},
    "1.4.1": {2, 3}, "1.4.2": {2, 3}, "1.4.3": {2, 3},
    "1.5.1": {2, 3},
    "2.1.1": {2, 3}, "2.1.2": {2, 3},
    "2.2.1": {2, 3}, "2.2.2": {2}, "2.2.3": {2, 3}, "2.2.4": {2},
    "2.3.1": set(), "2.3.2": set(),
    "2.4.1": {2}, "2.4.2": {2, 3},
    "2.5.1": {2, 3}, "2.5.2": {2, 3}, "2.5.3": {2, 3},
    "3.1.1": {2}, "3.1.2": {2}, "3.1.3": {2},
    "3.2.1": set(),
    "3.3.1": {2}, "3.3.2": {2}, "3.3.3": set(),
    "3.4.1": set(), "3.4.2": set(),
    "3.5.1": {2, 3}, "3.5.2": {2},
}

POST_DEC_CHOICES: List[str] = [
    "Park safely and request instructions",
    "Park safely and replan the route",
    "Emergency evacuation based on actual conditions",
    "Wait for avoidance and proceed straight ahead",
    "Wait for avoidance and take a detour",
    "Low-speed straight passage",
    "Accelerate straight passage",
    "Slow down and take a detour",
    "Accelerate the detour by taking a detour",
    "Wait for avoidance and depending on the situation, proceed straight ahead or take a detour",
]

POST_POLICY_CHOICES: List[str] = [
    "POLICY_LOCAL_PASS_WITH_CAUTION",
    "POLICY_SHORT_WAIT_AND_MONITOR",
    "POLICY_LOCAL_DETOUR_OR_REPOSITION",
    "POLICY_EVACUATE_AND_WARN",
]

POST_DEC_TO_POLICY: Dict[str, str] = {
    "Park safely and request instructions": "POLICY_LOCAL_DETOUR_OR_REPOSITION",
    "Park safely and replan the route": "POLICY_LOCAL_DETOUR_OR_REPOSITION",
    "Emergency evacuation based on actual conditions": "POLICY_EVACUATE_AND_WARN",
    "Wait for avoidance and proceed straight ahead": "POLICY_SHORT_WAIT_AND_MONITOR",
    "Wait for avoidance and take a detour": "POLICY_LOCAL_DETOUR_OR_REPOSITION",
    "Wait for avoidance and depending on the situation, proceed straight ahead or take a detour": "POLICY_SHORT_WAIT_AND_MONITOR",
    "Low-speed straight passage": "POLICY_LOCAL_PASS_WITH_CAUTION",
    "Accelerate straight passage": "POLICY_LOCAL_PASS_WITH_CAUTION",
    "Slow down and take a detour": "POLICY_LOCAL_DETOUR_OR_REPOSITION",
    "Accelerate the detour by taking a detour": "POLICY_LOCAL_DETOUR_OR_REPOSITION",
}

POST_DEC_TO_LEVEL: Dict[str, int] = {
    "Low-speed straight passage": 1,
    "Accelerate straight passage": 1,
    "Slow down and take a detour": 1,
    "Accelerate the detour by taking a detour": 1,
    "Wait for avoidance and proceed straight ahead": 2,
    "Wait for avoidance and take a detour": 2,
    "Wait for avoidance and depending on the situation, proceed straight ahead or take a detour": 3,
    "Park safely and request instructions": 4,
    "Park safely and replan the route": 4,
    "Emergency evacuation based on actual conditions": 5,
}

POLICY_ORDER: Dict[str, int] = {name: i + 1 for i, name in enumerate(POST_POLICY_CHOICES)}


class DecisionLabel(Enum):
    INVALID = '0'
    OPTIMAL = '1'
    SAFE = '2'
    RISKY = '3'
    HAZARDOUS = '4'

    @classmethod
    def from_string(cls, value: str) -> 'DecisionLabel':
        mapping = {
            '0': cls.INVALID, '1': cls.OPTIMAL, '2': cls.SAFE,
            '3': cls.RISKY, '4': cls.HAZARDOUS
        }
        return mapping.get(str(value), cls.INVALID)

    @property
    def description(self) -> str:
        descs = {
            '0': "Invalid/Collision",
            '1': "Optimal (GT)",
            '2': "Safe Alternative",
            '3': "Risky",
            '4': "Hazardous",
        }
        return descs.get(self.value, "Unknown")


class Stage(Enum):
    CLASSIFICATION = "stage1"
    PRE_DECISION = "stage2"
    REASONING = "stage3"
    LONGTAIL_CHECK = "stage3_is_longtail_only"

    @property
    def display_name(self) -> str:
        names = {
            "stage1": "Perception",
            "stage2": "Instant Decision",
            "stage3": "Post Decision-Making",
            "stage3_is_longtail_only": "Long-tail Check (GT=False)",
        }
        return names.get(self.value, self.value)
