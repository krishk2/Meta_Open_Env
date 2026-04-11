import os
import json
import textwrap
from typing import List, Optional
from openai import OpenAI

from client import CaseSolverEnv
from models import Action

IMAGE_NAME = os.getenv("IMAGE_NAME", "case_solver_env:latest") 
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

TASK_NAME = os.getenv("TASK_NAME", "case_solver")
BENCHMARK = os.getenv("BENCHMARK", "case_solver_env")
MAX_STEPS = 12
TEMPERATURE = 0.7
MAX_TOKENS = 150
SUCCESS_SCORE_THRESHOLD = 0.5  # normalized score in [0, 1]

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an AI detective. 
    Review the current state, facts, clues, and history to choose the single best investigative action.
    Reply strictly with exactly one JSON object: {"action_type": "<action_type>", "target_id": "<target>"}
    If you decide to interrogate or conclude_case, you MUST provide a valid target_id from the suspects list.
    """
).strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


def build_user_prompt(step: int, obs, last_reward: float, history: List[str]) -> str:
    history_block = "\n".join(history[-4:]) if history else "None"
    return textwrap.dedent(
        f"""
        Step: {step}
        Case Facts: {obs.initial_facts}
        Clues Extracted: {obs.discovered_clues}
        Available Actions: {obs.available_actions}
        Valid Targets: {obs.valid_targets}
        Last Reward: {last_reward:.2f}
        
        Recent steps history:
        {history_block}
        
        Send your next JSON action.
        """
    ).strip()


def get_model_action(client: OpenAI, step: int, obs, last_reward: float, history: List[str]) -> Action:
    user_prompt = build_user_prompt(step, obs, last_reward, history)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        data = json.loads(text)
        return Action(action_type=data.get("action_type", "search_past_cases"), target_id=data.get("target_id"))
    except Exception as exc:
         # Fallback action on failure
        action = Action(action_type="search_past_cases")
        if obs.available_actions and obs.time_remaining <= 2:
            action = Action(action_type="conclude_case", target_id=obs.valid_targets[0] if obs.valid_targets else None)
        elif obs.available_actions and "check_cctv" in obs.available_actions:
            action = Action(action_type="check_cctv")
        return action


async def run_episode(env: CaseSolverEnv, client: OpenAI, case_idx: int):
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    task_id = f"{TASK_NAME}_case_{case_idx}"
    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset()
        obs = result.observation
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            if result.done or obs.done:
                break

            action = get_model_action(client, step, obs, last_reward, history)

            result = await env.step(action)
            obs = result.observation

            reward = result.reward or 0.0
            done = result.done or obs.done
            
            # The environment step result might optionally contain metadata Dict
            info = obs.metadata or {}
            error = info.get("error")

            action_str = f"{action.action_type}(target={action.target_id})"

            rewards.append(reward)
            steps_taken = step
            last_reward = reward

            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            history.append(f"Step {step}: {action_str} -> reward {reward:+.2f}")

            if done:
                # Capture grader score returning from our environment on conclusion
                if "score" in info:
                    score = float(info["score"])
                break

        score = min(max(score, 0.0), 1.0)  # clamp to [0, 1]
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Error during episode: {e}", flush=True)
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    try:
        # Full Async workflow against local server directly
        async with CaseSolverEnv(base_url="http://localhost:8000") as env:
            for case_idx in range(3):
                await run_episode(env, client, case_idx)
    except Exception as e:
        print(f"[DEBUG] env integration error: {e}", flush=True)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
