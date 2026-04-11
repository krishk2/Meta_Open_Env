# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Case Solver Env Environment.
"""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import Action as CaseSolverAction
    from ..models import Observation as CaseSolverObservation
    from .case_solver_env_environment import CaseSolverEnvironment
except (ModuleNotFoundError, ImportError):
    from models import Action as CaseSolverAction
    from models import Observation as CaseSolverObservation
    from server.case_solver_env_environment import CaseSolverEnvironment


# Create the app with web interface and README integration
app = create_app(
    CaseSolverEnvironment,
    CaseSolverAction,
    CaseSolverObservation,
    env_name="case_solver_env",
    max_concurrent_envs=1, 
)


def main():
    """
    Standard entry point for the OpenEnv validator.
    This function must be callable without arguments to pass Step 3.
    """
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Using the string "server.app:app" allows the validator to find the 
    # app object correctly during isolated testing.
    uvicorn.run("server.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()