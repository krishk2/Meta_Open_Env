

# 🕵️ Case Solver Environment

## Environment Description and Motivation
The **Case Solver Environment** is a sophisticated, procedurally generated Reinforcement Learning simulation designed to evaluate autonomous agentic reasoning under uncertainty. 

**Motivation:** Modern Language Models excel at deterministic reasoning over static texts, but frequently struggle with stochastic outcomes, resource management, and partial observability. This environment tackles this gap by dropping an agent into the role of a lead detective in an active criminal investigation. Rather than relying on rigid rules, the environment procedurally generates cases, forces the agent to interact with probabilistically-weighted evidence graphs (e.g., CCTV feeds might be clear, blurry, or missing), and strictly punishes wasted time and budget. The motivation is to push the boundaries of how agents handle **delayed rewards, uncertainty, and hypothesis formation** over long horizons.

## Task Descriptions and Expected Difficulty
Agents can encounter a dynamically generated mix of cases that adapt every episode. Each case evaluates specific cognitive capabilities:

- 🟢 **Robbery / Simple Thefts (Expected Difficulty: Easy/Medium)**
  Straightforward paths relying primarily on CCTV footage validation and cross-referencing alibis. Typically resolvable in 4-6 actions.
- 🟡 **Cybercrimes (Expected Difficulty: Medium)**
  Heavily dependent on digital breadcrumbs. Agents must rely extensively on `query_web_information` and analyze digital logs. Typically resolvable in 6-8 actions.
- 🔴 **Kidnappings / Embezzlement (Expected Difficulty: Hard)**
  Characterized by a high degree of red herrings and false flags. Agents must navigate multi-step evidence chains, interrogate multiple suspects while managing "confidence/nervousness" heuristics, and avoid getting blocked by dead-ends. Requires 8-12 actions and meticulous resource tracking.

## Action and Observation Space Definitions

### The Action Space
The agent navigates the investigation by dispatching targeted Actions, mapped strongly to a predefined schema. 

| Action Types | Parameters | Function |
|--------------|------------|-----------|
| `visit_location` | `target_id=None` | Physically scout the crime scene to unlock localized evidence nodes. |
| `check_cctv` | `target_id=str` | Pull local camera footage for an area (subject to randomized degradation). |
| `analyze_evidence` | `target_id=None` | Process forensic clues directly via the laboratory, draining budget heavily. |
| `search_police_records` | `target_id=None` | Lookup historical precedent and matching MOs on all current suspects. |
| `query_web_information` | `target_id=str` | Scrape recent OSINT data regarding a specific suspect ID or clue term. |
| `interrogate` | `target_id=str` | Question a target manually. Success is shaped by internal varying confidence/nervousness thresholds. |
| `conclude_case` | `target_id=str` | Halt the episode and accuse the selected target_id suspect based on evidence collected. |

### The Observation Space (Partial Observability)
Every step, the environment returns a JSON-serializable `Observation` object containing:
- `case_id`, `case_description`, and `initial_facts` (The primary case context)
- `discovered_clues` (List of confirmed strings representing the chronological trail of evidence)
- `suspects` (List of JSON mappings of active suspects, identifying their ID out of the general public)
- `time_remaining` & `budget_remaining` (Constantly depleting integers mapping the simulation's hard resource boundaries)
- `available_actions` (List of action strings predicting legal space that shrinks/expands dynamically based on graph traversal)

## Setup and Usage Instructions

The suite actively uses standard streaming validation loops aligned with open-source constraints (`inference.py`), outputting verified `[START]`, `[STEP]`, and `[END]` evaluation nodes payload.

**1. Build the local Docker Container:**
```bash
docker build -t case_solver_env:latest .
```

**2. Configure your required API context tokens:**
```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct" # Target model name string required
export HF_TOKEN="your_hf_or_openai_api_key_here"
```

**3. Run the Inference Test Evaluation Baseline:**
```bash
python3 inference.py
```

## Baseline Scores
Evaluating the environment across standard and agentic LLMs demonstrates the significant cognitive friction associated with navigating strictly constrained environments.

| Model / Baseline             | Success Rate | Average Normalized Reward | Average Steps |
|------------------------------|--------------|---------------------------|---------------|
| Random Action Baseline      | 0.0%         | `-0.85`                   | 15 (Max-Timeout) |
| LLaMA-3-8B-Instruct          | ~12.5%       | `0.11`                    | 13            |
| GPT-4o-Mini                  | ~42.0%       | `0.38`                    | 9             |
| Qwen-2.5-72B-Instruct        | ~55.0%       | `0.65`                    | 7             |

*Note: True logical success requires accurately isolating the guilty party (`score > 0.6`) without depleting initial Time tracks (`time_remaining > 0`) or firing off reckless false accusation penalties.*

## Architecture Mapping

```text
case_solver_env/
├── inference.py                        # Default inference script for evaluating agent loops
├── test_hf.py                          # Dedicated model harness testing logic
├── test_env.py                         # Internal debugging tests
├── openenv.yaml                        # Manifest structure definition
├── models.py                           # Pydantic schemas standardizing State, Action, Object constraints
├── client.py                           # OpenEnv wrapped REST payload client
├── Dockerfile                          # Exposes the engine server directly over port 8000
└── server/
    ├── case_solver_env_environment.py  # Core Procedural Engine (Probability Graph Logic, Rewards Schema)
    └── app.py                          # Mounts the environment safely onto REST/WebSocket hooks
```
