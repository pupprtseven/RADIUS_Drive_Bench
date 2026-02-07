"""Prompt templates.

Maintain templates in a single file so you can iterate without hunting through the pipeline logic.
"""

PROMPTS = {
    "judge_lt_ele": {
        "system": "You are an expert evaluator for autonomous driving scene understanding. Score the similarity between predicted and ground truth long-tail element descriptions. Always respond in JSON format.",
        "user": """## Task: Evaluate Long-tail Element Recognition

### Ground Truth:
{gt_lt_ele}

### Prediction:
{pred_lt_ele}

### Scoring Criteria (0-10):
- 10: Perfect match - identical or semantically equivalent description
- 7-9: High similarity - captures the main element with minor differences
- 4-6: Partial match - identifies related element but misses key aspects
- 1-3: Low similarity - vaguely related but significantly different
- 0: No match - completely different or irrelevant

### Required Output (JSON):
{{
    "score": <integer 0-10>,
    "reasoning": "brief explanation"
}}""",
    },
    "judge_acc_factors": {
        "system": "You are an expert evaluator for autonomous driving passability analysis. Always respond in JSON format.",
        "user": """## Task: Evaluate Passability Factors Analysis

### Ground Truth Factors:
{gt_factors}

### Predicted Factors:
{pred_factors}

### Scoring Criteria (0-10):
- 10: All critical factors identified with accurate analysis
- 7-9: Most factors identified, minor omissions
- 4-6: Some factors identified, missing important ones
- 1-3: Few factors identified, major gaps
- 0: No relevant factors identified

### Required Output (JSON):
{{
    "score": <integer 0-10>,
    "reasoning": "brief explanation"
}}""",
    },
    "judge_cot": {
        "system": (
            "You are a STRICT and skeptical evaluator for autonomous-driving reasoning quality. "
            "You must be evidence-bound: do NOT assume any scene details that are not explicitly provided. "
            "High scores (9-10) must be rare."
        ),
        "user": """## Task: Strictly Evaluate Chain-of-Thought (COT) Quality for Post-Decision Reasoning

You are given limited context. Judge reasoning quality using ONLY the evidence below.

Important clarifications:
- The "Executed action" (vx, ay) is the *commanded/selected action for this step*, NOT the measured ego speed.
- The "post-decision policy" is an abstract label; the COT may paraphrase it (e.g., "wait/hold" for POLICY_SHORT_WAIT_AND_MONITOR).
- Proposing alternative actions/policies is allowed. Treat them as hallucinations ONLY if they are asserted as *observed scene facts*.
- If the COT introduces extra *scene details* (positions, distances, signals, lane counts, new objects/events), treat them as hallucinations.
- If the COT includes numeric speeds or exact locations, treat them as hallucinations unless explicitly stated in Allowed Evidence.

### Mode & Context
- Stage3 mode: {mode}
- Context used to generate this COT (mode_context):
  - is_longtail: {ctx_is_longtail}
  - Classification (level3): {ctx_level3}
  - Long-tail element (choice): {ctx_lt_ele}

### Ground-truth context (if available)
- GT Classification (level3): {gt_level3}
- GT Long-tail element (choice): {gt_lt_ele}

### Allowed Evidence (ONLY these; everything else is NOT verifiable):
- Executed action (command): vx={vx}, ay={ay}
- Derived motion tag (approx): {current_state}
- Predicted post-decision (natural language): {post_dec_pred}
- Predicted high-level post-decision policy: {post_policy_pred}
- Ground-truth post-decision (natural language, if available): {post_dec_gt}
- Ground-truth post-decision policy (if available): {post_policy_gt}
- Passability factors summary (may be a list of factor phrases): {acc_factors}
- Ground-truth reasoning reference (if available): {gt_cot}

### Predicted Chain-of-Thought (to evaluate):
{pred_cot}

---

## Step 0: Context Alignment Gate (high weight; distinguishes modes)
If both GT Classification and GT Long-tail element are NOT "N/A":
- If mode_context uses "UNKNOWN" for classification or long-tail element -> score MUST be <= 6.
- If mode_context classification differs from GT classification -> deduct 2 points.
- If mode_context long-tail element differs from GT long-tail element -> deduct 2 points.
Important: do NOT reward a COT that is well-written but anchored on the WRONG hazard/category when GT is available.

## Step A: Evidence Audit (hard requirement)
1) Extract 2-3 concrete claims from the predicted COT.
2) For EACH claim, state whether it is explicitly supported by the Allowed Evidence above OR by the mode_context.

Definitions:
- "Supported" means directly implied by Allowed Evidence or mode_context (not guessed).
- "Hallucination / Unverifiable detail" includes:
  - Any object IDs, exact positions, distances, lane counts, traffic light states, etc.
  - Any physical assertions not present in Allowed Evidence or mode_context.
  - Any new hazards beyond the mode_context long-tail element ({ctx_lt_ele}) that are not stated in mode_context.
  - NOTE: Mentioning an action/policy (e.g., "detour", "park", "wait") is NOT a hallucination if it is
    (a) consistent with the provided predicted/GT post-decision text/policy, or (b) clearly presented as a hypothetical alternative.

Scoring gates:
- If < 2 supported claims can be found -> score MUST be <= 4.
- If ANY hallucination/unverifiable detail exists -> deduct heavily and score MUST be <= 6.

## Step B: Consistency & Completeness Checks (must be explicit in the COT)
Check whether the COT explicitly addresses ALL of the following:
B1) Does the long-tail element block the planned straight route? (must be consistent with {acc_factors})
B2) Lane-borrowing feasibility (must be consistent with {acc_factors})
B3) Why the executed action (vx, ay) is appropriate for the chosen policy OR explicitly acknowledges it is only a “reasoning action” and does not overclaim dynamics.
B4) Clear causal chain: observation -> risk -> alternatives -> chosen policy.
Missing any item B1-B4: -2 points each.

Synonyms that count (do NOT penalize if expressed this way):
- For B1: "cannot proceed straight", "forward progress is blocked/impeded", "path ahead is blocked".
- For B1: "affects own vehicle's passage", "straight route affected/blocked".
- For B2: "lane change/borrow is unavailable", "temporarily blocked", "no feasible lane-borrowing", "lane-borrowing possible".

## Step C: Alternatives (distinguish good from generic)
The COT must compare at least TWO plausible alternative policies/actions and explain why they are worse/less safe.
- Generic phrases like “other actions are risky” without specific comparison do NOT count.
If alternatives are missing or generic -> cap score at 7.

## Step D: Use of Ground-truth (if provided)
If {gt_cot} is not N/A:
- Penalize if the predicted COT misses key risk factors, misstates the blocking/borrowability logic, or chooses an incompatible policy rationale. (-1 to -3)

---

## Scoring (0-10 integer; start at 10 and subtract)
Guidance (be strict):
- 9-10: Exceptionally precise, evidence-bound, no hallucinations, correct alignment with GT (if available), strong alternatives comparison.
- 7-8: Mostly solid and evidence-bound, minor omissions, no hallucinations, aligned with GT or GT not provided.
- 5-6: Some grounding but generic/incomplete; OR contains small unverifiable details (must be <= 6 if any hallucination exists); OR context is UNKNOWN.
- 0-4: Largely generic, unsupported, hallucinated/unverifiable, or anchored on wrong hazard/category when GT is available.

### Required Output (JSON):
{{
  "score": <integer 0-10>,
  "reasoning": "Brief: list key deductions (context mismatch, hallucinations, missing B1-B4, weak alternatives, inconsistencies)."
}}""",
    },
    "stage1": {
        "system": "You are an expert in autonomous driving perception and passability assessment. Analyze driving scenes and identify potential hazards with high precision. Always respond in JSON format.",
        "user": """Analyze the provided driving scene image.

## Supplemental description (Sup_description, if provided):
{sup_description}
Note: Sup_description is auxiliary. If it conflicts with the image, the image is the source of truth.

## Classification Taxonomy (3 Levels):
{taxonomy}

## Long-tail element single-choice list (0-based index):
{lt_ele_choices}

## Structured passability factors (multiple choice):
{acc_factors_choices}

## Classification Guidelines:
- Category 1 (Fully Closed): Lane closures due to various reasons requiring emergency operations (brake, lane change, detour, turn around)
- Category 2 (Semi-Closed): Lanes with obstacles or temporary traffic rule changes requiring judgment on passability and safe passage
- Category 3 (Surface Open but Risks): Lane surface is clear but there are hidden risks requiring vigilance

## Task:
1. Determine if this scene contains long-tail (rare/unusual) elements.
2. Classify the scene to the most specific level (level3) according to the taxonomy above.
3. Choose exactly **one** long-tail element from the list above (use index 0 = "None of the above / No long-tail element" if none), and optionally give a short free-text description.
4. For each passability factor group, choose **one** most appropriate option.
5. Provide a brief passability summary text (acc_factors_text).

## Required Output (JSON):
{{
    "is_longtail": "True" or "False",
    "level1": "1" | "2" | "3" | "N/A",
    "level2": "X.Y" | "N/A",
    "level3": "X.Y.Z" | "N/A",
    "lt_ele_idx": <integer, 0-{max_idx}>,
    "lt_ele_choice": "<copy exact string from list>",
    "lt_ele_text": "optional free-text description",
    "acc_factors_multi": {{
        "group1_idx": <integer 1-{g1_max}>,
        "group1_choice": "<copy from Group 1>",
        "group2_idx": <integer 1-{g2_max}>,
        "group2_choice": "<copy from Group 2>",
        "group3_idx": <integer 1-{g3_max}>,
        "group3_choice": "<copy from Group 3>"
    }},
    "acc_factors_text": "short free-text summary about passability"
}}

Respond ONLY with valid JSON, no additional text.""",
    },
    "stage2": {
        "system": "You are an autonomous vehicle safety controller for instant decision-making. Your primary objective is collision avoidance through optimal action selection. Always respond in JSON format.",
        "user": """## Planned Route (default):
Proceed straight in the current lane unless safety requires avoidance.

## Current Vehicle State (from pre_dec_json, auxiliary):
{map_description}
Note: If the structured state conflicts with the image, follow the image.

## Available Action Space:
- Lateral velocity (vx): {vx_options}
  - Negative values = move left
  - Positive values = move right
  - Unit: unit/s  (spatial unit per second)

- Longitudinal acceleration (ay): {ay_options}
  - Negative values = brake/decelerate
  - Positive values = accelerate
  - Unit: unit/s^2 (spatial unit per second^2)

Scale reference: 1 unit = 0.02 m (2 cm). Therefore 1 unit/s = 0.02 m/s and 1 unit/s^2 = 0.02 m/s^2.

## Collision checking abstraction (must follow):
- Treat every object as an axis-aligned rectangle.
- Expand each rectangle by +8 unit on each side, then check collisions.
- For pedestrian-type rectangles: expand by +15 unit on each side, then check collisions.
- For out-of-control vehicles: expand by +35 unit on each side, then check collisions.
- Your selected action must ensure **no collision within the next 3 seconds** under this collision-checking abstraction.

## Task:
Select the optimal action to safely continue the planned straight route (or safely avoid obstacles if straight is blocked).

## Required Output (JSON):
{{
    "selected_vx": <integer from vx options>,
    "selected_ay": <integer from ay options>,
    "reasoning_brief": "1-2 sentence explanation"
}}

Respond ONLY with valid JSON, no additional text.""",
    },
    "stage3_is_longtail_only": {
        "system": (
            "You are an autonomous-driving safety reviewer. "
            "Decide whether the scene contains any long-tail (rare/unusual) element based on the provided taxonomy. "
            "Respond ONLY in JSON."
        ),
        "user": """Review the scene image and structured context to decide if it is a long-tail case.

## Supplemental description (Sup_description, if provided):
{sup_description}
Note: Sup_description is auxiliary. If it conflicts with the image/map, follow the image.

## Structured map context (auxiliary for relative objects/ego state):
{map_description}

## Long-tail classification baseline:
{taxonomy}

## Long-tail element single-choice list (0-based index):
{lt_ele_choices}

## Guidance:
- Long-tail = rare or unusual hazards/events (closures, abnormal obstacles/behaviors, severe surface issues, special events).
- Routine free-flow traffic, normal pedestrians/vehicles following rules, or light/common conditions → usually NOT long-tail.
- If evidence is unclear, lean toward "False" (not long-tail).
- ONLY decide whether any long-tail element exists; no need to output classification codes.

## Required Output (JSON):
{{
  "is_longtail": "True" | "False",
  "reason": "1-2 sentence justification"
}}

Respond ONLY with valid JSON, no additional text.""",
    },
    "stage3_longtail_assist": {
        "system": "",
        "user": """Analyze the scene image and structured context for post-stop decision-making.

## Important mode notes:
- Ground truth says this is long-tail (is_longtail=True). Do NOT re-evaluate; set is_longtail="True" in output.
- Instant decision was skipped; the provided action (vx, ay) is for context only.

## Supplemental description (Sup_description, if provided):
{sup_description}
Note: Sup_description is auxiliary. If it conflicts with the image/map, the image is the source of truth.

## Structured map context (auxiliary for relative objects/ego state):
{map_description}

## Available taxonomies and choices:
- Classification taxonomy (3 levels):
{taxonomy}
- Long-tail element single-choice list (0-based index):
{lt_ele_choices}
- Structured passability factors (multiple choice):
{acc_factors_choices}

## Instant decision context (for reference only):
- Provided action: vx={vx}, ay={ay}
- Motion tag (approx): {current_state}

## Task (assume is_longtail=True):
1) Keep is_longtail="True" and classify to the most specific level (level3).
2) Choose exactly one long-tail element (lt_ele_idx + lt_ele_choice) and optional free-text description.
3) Select passability factors for each group (acc_factors_multi) and give a short summary (acc_factors_text).
4) Immediately evaluate which passability factor groups actually influence the **post-decision** (acc_effective_indices).
   - Use ONLY indices 1/2/3 corresponding to the three groups above.
   - Mark a group effective only if it truly changes the post decision for this long-tail type; do NOT add extra factors.
5) Provide a concise chain-of-thought (COT) explaining hazard classification, passability, which factors are effective, and the next action choice.
6) Propose a free-text post-decision plan (post_decision_plan) AND an abstract intent label (post_decision_style) in natural language (e.g., "cautious immediate passage", "wait then detour", "park/replan", "evacuate").

## Output format (JSON):
{{
  "is_longtail": "True",
  "level1": "1" | "2" | "3" | "N/A",
  "level2": "X.Y" | "N/A",
  "level3": "X.Y.Z" | "N/A",
  "lt_ele_idx": <integer>,
  "lt_ele_choice": "<copy exact string from list>",
  "lt_ele_text": "optional short description",
  "acc_factors_multi": {{
    "group1_idx": <integer>,
    "group1_choice": "<copy from Group 1>",
    "group2_idx": <integer>,
    "group2_choice": "<copy from Group 2>",
    "group3_idx": <integer>,
    "group3_choice": "<copy from Group 3>"
  }},
  "acc_factors_text": "short free-text summary",
  "acc_effective_indices": [<integers drawn from 1,2,3; no extras>],
  "acc_effective_notes": {{
    "1": "why group1 is (not) effective for the final decision",
    "2": "...",
    "3": "..."
  }},
  "COT": "concise rationale linking hazard -> passability -> effective factors -> post decision",
  "post_decision_plan": "free-text description of the next handling step",
  "post_decision_style": "free-text abstract intent (e.g., cautious immediate passage / wait then detour / park & replan / evacuate)"
}}

Constraints:
- Keep is_longtail fixed to \"True\".
- Stay abstract: no distances/IDs/counts beyond the provided context.
- Keep acc_effective_indices to the existing three groups; do NOT invent new groups.
""",
    },
    "stage3": {
        "system": (
            "You are an autonomous driving planner that MUST jointly perceive long-tail hazards, "
            "assess passability factors, judge which factors truly influence the final decision, "
            "and propose a post-decision handling plan (free text; no numeric level). Always respond in JSON."
        ),
        "user": """Analyze the scene image and structured context to complete a **single end-to-end decision**.

## Supplemental description (Sup_description, if provided):
{sup_description}
Note: Sup_description is auxiliary. If it conflicts with the image/map, the image is the source of truth.

## Structured map context (auxiliary for relative objects/ego state):
{map_description}

## Available taxonomies and choices:
- Classification taxonomy (3 levels):
{taxonomy}
- Long-tail element single-choice list (0-based index):
{lt_ele_choices}
- Structured passability factors (multiple choice):
{acc_factors_choices}

## Instant decision outcome (for collision avoidance reference):
- Selected action: vx={vx}, ay={ay}
- Action label: {decision_label} ({decision_label_desc})
- Motion tag (approx): {current_state}

## Task (do all steps in one pass):
1) Determine if this is a long-tail scene and classify to the most specific level (level3).
2) Choose exactly one long-tail element (lt_ele_idx + lt_ele_choice) and optional free-text description.
3) Select passability factors for each group (acc_factors_multi) and give a short summary (acc_factors_text).
4) Immediately evaluate which passability factor groups actually influence the **post-decision** (acc_effective_indices).
   - Use ONLY indices 1/2/3 corresponding to the three groups above.
   - Mark a group effective only if it truly changes the post decision for this long-tail type; do NOT add extra factors.
5) Provide a concise chain-of-thought (COT) explaining hazard classification, passability, which factors are effective, and the next action choice.
6) Propose a free-text post-decision plan (post_decision_plan) AND an abstract intent label (post_decision_style) in natural language (e.g., "cautious immediate passage", "wait then detour", "park/replan", "evacuate").

## Output format (JSON):
{{
  "is_longtail": "True" | "False",
  "level1": "1" | "2" | "3" | "N/A",
  "level2": "X.Y" | "N/A",
  "level3": "X.Y.Z" | "N/A",
  "lt_ele_idx": <integer>,
  "lt_ele_choice": "<copy exact string from list>",
  "lt_ele_text": "optional short description",
  "acc_factors_multi": {{
    "group1_idx": <integer>,
    "group1_choice": "<copy from Group 1>",
    "group2_idx": <integer>,
    "group2_choice": "<copy from Group 2>",
    "group3_idx": <integer>,
    "group3_choice": "<copy from Group 3>"
  }},
  "acc_factors_text": "short free-text summary",
  "acc_effective_indices": [<integers drawn from 1,2,3; no extras>],
  "acc_effective_notes": {{
    "1": "why group1 is (not) effective for the final decision",
    "2": "...",
    "3": "..."
  }},
  "COT": "concise rationale linking hazard -> passability -> effective factors -> post decision",
  "post_decision_plan": "free-text description of the next handling step",
  "post_decision_style": "free-text abstract intent (e.g., cautious immediate passage / wait then detour / park & replan / evacuate)"
}}

Constraints:
- Stay abstract: no distances/IDs/counts beyond the provided context.
- Keep acc_effective_indices to the existing three groups; do NOT invent new groups.
- post_decision_level must be 1-5 (integers).""",
    },
    "judge_post_level": {
        "system": (
            "You are a strict evaluator that maps an autonomous-driving post-decision rationale "
            "to an abstract level 1-5. Respond ONLY in JSON."
        ),
        "user": """## Post-decision level mapping (choose the single best level):
- Level 1: Immediate local passage (straight or detour) with speed control.
- Level 2: Wait/avoidance first, then proceed (straight or detour).
- Level 3: Wait first, then choose straight vs detour depending on situation.
- Level 4: Park safely and request instructions OR replan the route.
- Level 5: Emergency evacuation / leave area entirely.

## Evidence to map:
- Long-tail classification (level3): {level3}
- Long-tail element: {lt_ele}
- Passability factors: {acc_factors_text}
- Effective factors (groups that matter): {acc_effective_indices}
- Post-decision plan (free text): {post_decision_plan}
- Chain-of-thought (reasoning): {cot}
- Ground-truth post_dec level (if available): {gt_post_dec_level}

## Instructions:
- Use the reasoning and plan to pick the most suitable level (1-5).
- Ignore wording style; focus on the actual intent (wait/park/evacuate/pass).
- If the plan is ambiguous between two adjacent levels, choose the more conservative one.

## Required Output (JSON):
{{
  "score": <integer 1-5>,
  "reasoning": "brief note on why this level fits best",
  "max_score": 5
}}""",
    },
}
