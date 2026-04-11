import json
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Case Solver Env Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from models import Action as CaseSolverAction
from models import Observation as CaseSolverObservation


class CaseSolverEnv(
    EnvClient[CaseSolverAction, CaseSolverObservation, State]
):
    """
    Client for the Case Solver Env Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions with lower latency.
    Each client instance has its own dedicated environment session on the server.

    Example:
        >>> # Connect to a running server
        >>> with CaseSolverEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.case_description)
        ...
        ...     result = client.step(CaseSolverAction(action_type="check_cctv"))
        ...     print(result.observation.discovered_clues)

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = CaseSolverEnv.from_docker_image("case_solver_env-env:latest")
        >>> try:
        ...     result = client.reset()
        ...     result = client.step(CaseSolverAction(action_type="interrogate", target_id="S1"))
        ... finally:
        ...     client.close()
    """

    def _step_payload(self, action: CaseSolverAction) -> Dict:
        """
        Convert CaseSolverAction to JSON payload for step message.

        Args:
            action: CaseSolverAction instance

        Returns:
            Dictionary representation suitable for JSON encoding
        """
        return action.model_dump(exclude_none=True)

    def _parse_result(self, payload: Dict) -> StepResult[CaseSolverObservation]:
        """
        Parse server response into StepResult[CaseSolverObservation].

        Args:
            payload: JSON response data from server

        Returns:
            StepResult with CaseSolverObservation
        """
        obs_data = payload.get("observation", {})
        print(f"[PAYLOAD_DEBUG] /step -> {json.dumps(payload)}")
        # The OpenEnv wrappers extract the observation's nested metadata dict to the root JSON object as "info".
        # We manually repack it into the observation prior to client validation to ensure 'score' doesn't vanish.
        info_dict = payload.get("info", {})
        if info_dict:
            obs_data["metadata"] = info_dict
            
        observation = CaseSolverObservation.model_validate(obs_data)

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """
        Parse server response into State object.

        Args:
            payload: JSON response from state request

        Returns:
            State object with episode_id and step_count
        """
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
