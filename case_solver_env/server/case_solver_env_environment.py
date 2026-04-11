import random
import uuid
import math
from models import Action, Observation, Suspect
from openenv.core.env_server.interfaces import Environment


class MockExternalAPI:
    """Mock external APIs to simulate real-world integration without network calls."""
    @staticmethod
    def query_web_information(target: str) -> str:
        # Simulate a scraping/Wikipedia API
        responses = [
            f"Found an old forum post mentioning {target}.",
            f"News article states {target} was recently involved in a public dispute.",
            f"No significant recent web footprint found for {target}."
        ]
        return random.choice(responses)

    @staticmethod
    def search_past_cases(target: str) -> str:
        # Simulate a local / public database of past crimes
        responses = [
            f"Record found: {target} was investigated 2 years ago but cleared.",
            f"Record found: {target} has a history of similar minor offenses.",
            f"No past criminal records matching {target}."
        ]
        return random.choice(responses)

    @staticmethod
    def visit_location(location: str) -> str:
        # Simulate OpenStreetMap or location database
        responses = [
            f"The location at {location} is an abandoned warehouse.",
            f"The location at {location} is a busy commercial street.",
            f"The location at {location} seems to be a quiet residential area."
        ]
        return random.choice(responses)


class CaseSolverEnvironment(Environment):
    def __init__(self):
        self._state = None
        
        # Domains for dynamic procedural generation
        self.suspect_names = ["Rahul", "Amit", "Neha", "Karan", "Priya", "Vikram", "Sneha", "Rohan"]
        self.locations = ["Downtown Cafe", "Warehouse 42", "Main Street Bank", "Tech Park Cyber Center", "City Library", "Abandoned Factory"]
        self.crime_types = ["fraud", "robbery", "cybercrime", "kidnapping", "embezzlement"]
        self.motives = ["financial desperation", "revenge", "corporate espionage", "personal dispute"]

    # RESET
    def reset(self) -> Observation:
        self._state = self._generate_dynamic_case()
        return self._build_observation()

    # DYNAMIC CASE GENERATION
    def _generate_dynamic_case(self):
        crime = random.choice(self.crime_types)
        location = random.choice(self.locations)
        motive = random.choice(self.motives)
        
        # Generate 3-4 random suspects
        num_suspects = random.randint(3, 4)
        selected_suspect_names = random.sample(self.suspect_names, num_suspects)
        
        suspects = []
        for i, name in enumerate(selected_suspect_names):
            suspects.append({
                "id": f"S{i+1}",
                "name": name,
                "confidence": 0.0,
                "status": "unknown"
            })
            
        # Randomly select a culprit
        culprit = random.choice(suspects)
        
        # Pick an innocent suspect for misleading clues
        innocents = [s for s in suspects if s["id"] != culprit["id"]]
        innocent_pawn = random.choice(innocents) if innocents else culprit
        
        case_id = f"case_{crime}_{uuid.uuid4().hex[:6]}"
        
        description = f"Investigation of a {crime} that occurred at {location}. Suspected motive: {motive}."
        
        clue_graph = self._build_stochastic_clue_graph(crime, culprit, innocent_pawn, location)

        return {
            "case_id": case_id,
            "case_description": description,
            "solution": culprit["id"],
            "initial_facts": [f"Crime type: {crime}", f"Location: {location}"],
            "previous_case_history": ["Past trends suggest checking digital footprints and alibis."],
            "clue_graph": clue_graph,
            "suspects": suspects,
            
            # State tracking
            "discovered_clues": [],
            "unlocked_nodes": ["visit_location", "request_additional_data", "check_cctv"], # Initial entry points
            "steps_taken": 0,
            "done": False,
            "last_actions": [],
            "max_steps": 15,
            "time_remaining": 24, # In-game hours
            "budget_remaining": 500 # Investigation budget
        }

    # STOCHASTIC CLUE GRAPH GENERATION
    def _build_stochastic_clue_graph(self, crime, culprit, innocent_pawn, location):
        """
        Dynamically builds a graph of actions -> possible stochastic outcomes.
        This provides multiple paths and uncertain rewards.
        """
        return {
            "visit_location": {
                "cost_time": 2, "cost_budget": 20,
                "outcomes": [
                    {"prob": 0.5, "text": f"Found a physical receipt linking to {culprit['name']}.", "unlock": ["analyze_evidence", "search_police_records"], "reward": 0.3},
                    {"prob": 0.3, "text": f"Found partial footprints but they are unusable.", "unlock": [], "reward": 0.05},
                    {"prob": 0.2, "text": f"Misleading evidence pointing to {innocent_pawn['name']}.", "unlock": ["analyze_evidence"], "reward": -0.1}
                ]
            },
            "check_cctv": {
                "cost_time": 1, "cost_budget": 10,
                "outcomes": [
                    {"prob": 0.4, "text": f"Clear footage identifying {culprit['name']} near {location}.", "unlock": ["search_police_records"], "reward": 0.3},
                    {"prob": 0.3, "text": "Footage is blurry, but matches a vehicle model.", "unlock": ["analyze_evidence"], "reward": 0.1},
                    {"prob": 0.2, "text": "Camera was vandalized prior to the crime.", "unlock": ["query_web_information"], "reward": -0.05},
                    {"prob": 0.1, "text": f"Footage falsely identifies {innocent_pawn['name']}.", "unlock": ["search_police_records"], "reward": -0.2}
                ]
            },
            "analyze_evidence": {
                "cost_time": 3, "cost_budget": 50,
                "outcomes": [
                    {"prob": 0.6, "text": f"Lab results confirm traces belonging to {culprit['name']}.", "unlock": [], "reward": 0.4},
                    {"prob": 0.3, "text": "Results are inconclusive.", "unlock": [], "reward": 0.0},
                    {"prob": 0.1, "text": "Evidence was contaminated.", "unlock": [], "reward": -0.1}
                ]
            },
            "request_additional_data": {
                "cost_time": 2, "cost_budget": 100,
                "outcomes": [
                    {"prob": 0.5, "text": f"Cell tower data places {culprit['name']} at {location}.", "unlock": ["search_police_records"], "reward": 0.4},
                    {"prob": 0.3, "text": "Data logs are encrypted and will take too long to crack.", "unlock": [], "reward": 0.0},
                    {"prob": 0.2, "text": f"Spoofed IP address points to {innocent_pawn['name']}.", "unlock": [], "reward": -0.1}
                ]
            }
        }

    # ACTION FILTERING
    def _get_available_actions(self):
        # Only actions that are unlocked and have not been exhausted are fully available for graph traversal
        # But we also always allow certain general actions
        general_actions = ["interrogate", "search_past_cases", "query_web_information", "conclude_case"]
        dynamic_actions = [a for a in self._state["unlocked_nodes"] if a in self._state["clue_graph"]]
        return list(set(general_actions + dynamic_actions))

    # OBSERVATION
    def _build_observation(self, reward=0.0, metadata=None):
        meta = {"case_id": self._state["case_id"]}
        if metadata:
            meta.update(metadata)

        return Observation(
            case_id=self._state["case_id"],
            case_description=self._state["case_description"],
            initial_facts=self._state["initial_facts"],
            discovered_clues=self._state["discovered_clues"],
            previous_case_history=self._state["previous_case_history"],
            suspects=[Suspect(**s) for s in self._state["suspects"]],
            available_actions=self._get_available_actions(),
            time_remaining=self._state["time_remaining"],
            budget_remaining=self._state["budget_remaining"],
            steps_taken=self._state["steps_taken"],
            max_steps=self._state["max_steps"],
            done=self._state["done"],
            reward=reward,
            valid_targets=[s["id"] for s in self._state["suspects"]],
            metadata=meta,
            score=self._state.get("score")
        )

    # GRADER / REWARD SHAPING
    def _grade_solution(self, target):
        # Continuous grading scheme
        efficiency = max(0, 1 - (self._state["steps_taken"] / self._state["max_steps"]))
        budget_bonus = max(0, self._state["budget_remaining"] / 500.0) * 0.1
        time_bonus = max(0, self._state["time_remaining"] / 24.0) * 0.1

        if target == self._state["solution"]:
            # Correct culprit -> returns a positive score between [0.7, 1.0]
            return min(1.0, 0.7 + (0.1 * efficiency) + budget_bonus + time_bonus)
        else:
            # Wrong culprit
            return -0.5

    def _resolve_stochastic_clue(self, outcomes):
        r = random.random()
        cumulative = 0.0
        for outcome in outcomes:
            cumulative += outcome["prob"]
            if r <= cumulative:
                return outcome
        return outcomes[-1]

    # STEP
    def step(self, action: Action):
        if self._state["done"]:
            return self._build_observation()

        reward = -0.01  # Small step penalty to encourage speed
        info = {"action": action.action_type}
        
        self._state["steps_taken"] += 1
        
        # Loop penalty
        self._state["last_actions"].append(action.action_type)
        self._state["last_actions"] = self._state["last_actions"][-3:]
        if len(set(self._state["last_actions"])) == 1 and len(self._state["last_actions"]) == 3:
            reward -= 0.1 # Repeated action penalty

        action_type = action.action_type
        target = action.target_id
        
        # Handle the action
        if action_type in self._state["clue_graph"] and action_type in self._state["unlocked_nodes"]:
            node = self._state["clue_graph"][action_type]
            
            # Apply costs
            time_cost = node.get("cost_time", 1)
            budget_cost = node.get("cost_budget", 10)
            self._state["time_remaining"] -= time_cost
            self._state["budget_remaining"] -= budget_cost
            
            # Note: We let the state evaluation at the end determine the done=True condition
            # Resolve probabilistic outcome
            outcome = self._resolve_stochastic_clue(node["outcomes"])
            
            # Remove from unlocked nodes to enforce forward traversal and prevent agent looping
            if action_type in self._state["unlocked_nodes"]:
                self._state["unlocked_nodes"].remove(action_type)
            
            # Unlock new nodes
            for u in outcome.get("unlock", []):
                if u not in self._state["unlocked_nodes"]:
                    self._state["unlocked_nodes"].append(u)
                    
            if outcome["text"] not in self._state["discovered_clues"]:
                self._state["discovered_clues"].append(outcome["text"])
                reward += outcome["reward"]
                info["clue"] = outcome["text"]
            else:
                reward -= 0.05 # Re-discovering the same clue

        elif action_type == "interrogate":
            self._state["time_remaining"] -= 2
            
            # Increase confidence in the target suspect
            found = False
            for s in self._state["suspects"]:
                if s["id"] == target:
                    s["confidence"] = min(1.0, s["confidence"] + 0.25)
                    s["status"] = "suspected"
                    found = True
                    reward += 0.1
                    clue_text = f"Interrogated {s['name']}. They seemed nervous."
                    info["clue"] = clue_text
                    if clue_text not in self._state["discovered_clues"]:
                        self._state["discovered_clues"].append(clue_text)
            
            if not found:
                reward -= 0.1 # Invalid target string
                
        elif action_type == "query_web_information":
            self._state["time_remaining"] -= 1
            self._state["budget_remaining"] -= 5
            
            # Extract target name
            target_name = None
            if target:
                for s in self._state["suspects"]:
                    if s["id"] == target:
                        target_name = s["name"]
            
            api_res = MockExternalAPI.query_web_information(target_name or "unknown entity")
            if api_res not in self._state["discovered_clues"]:
                self._state["discovered_clues"].append(api_res)
            reward += 0.05
            info["clue"] = api_res

        elif action_type == "search_police_records":
            self._state["time_remaining"] -= 1
            self._state["budget_remaining"] -= 15
            
            # Same target finding
            target_name = None
            if target:
                for s in self._state["suspects"]:
                    if s["id"] == target:
                        target_name = s["name"]
            api_res = MockExternalAPI.search_past_cases(target_name or "unknown entity")
            if api_res not in self._state["discovered_clues"]:
                self._state["discovered_clues"].append(api_res)
            reward += 0.05
            info["clue"] = api_res
            
        elif action_type == "search_past_cases":
            self._state["time_remaining"] -= 2
            self._state["budget_remaining"] -= 10
            api_res = MockExternalAPI.search_past_cases("General trends")
            if api_res not in self._state["previous_case_history"]:
                self._state["previous_case_history"].append(api_res)
            reward += 0.05
            info["clue"] = api_res

        elif action_type == "conclude_case":
            self._state["done"] = True
            
            if len(self._state["discovered_clues"]) < 2:
                reward -= 0.5 # Premature conclusion penalty
                score = 0.0
            else:
                score = self._grade_solution(target) 
                reward += score
						score = round(score, 2)
            self._state["score"] = score
            # Handshaking the score logic properly as requested
            info["score"] = score 
            info["correct"] = target == self._state["solution"]

        else:
            # Action not supported or not unlocked
            reward -= 0.2
            info["error"] = f"Action {action_type} is not available or unrecognized."

        # Resource depletion logic
        if not self._state["done"] and (self._state["time_remaining"] <= 0 or self._state["budget_remaining"] <= 0):
            self._state["done"] = True
            reward -= 0.3
            info["reason"] = "Ran out of resources"

        # Max steps logic
        if not self._state["done"] and self._state["steps_taken"] >= self._state["max_steps"]:
            self._state["done"] = True
            reward -= 0.2

        # Finally normalize reward bounds explicitly to be robust between [-1.0, 1.0] just in case! 
        # (Though some training algorithms don't strictly require this, it's safer per the new feedback bounds).
        reward = max(-1.0, min(1.0, reward))
				reward = round(reward, 2)
        
        info["done"] = self._state["done"]
        return self._build_observation(reward, info)

    @property
    def state(self):
        from openenv.core.env_server.types import State
        return State(
            episode_id=self._state["case_id"] if self._state else "none",
            step_count=self._state["steps_taken"] if self._state else 0
        )