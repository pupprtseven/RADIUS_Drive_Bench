import copy
import numpy as np
from Py_Lightweight_IVI.evaluation_framework.core.scene import Scene


class Simulator:
    """
    Simulation scheduler responsible for executing the scene forward in time.

    The Simulator supports:
    - Running a single simulation rollout
    - Running multiple simulations with different ego control configurations
    - Recording ego trajectories and collision outcomes
    - Fitting a time-parameterized trajectory function for the ego vehicle
    """

    def __init__(self, scene: Scene, source_path: str, duration=3.2):
        """
        Initialize the simulator.

        Args:
            scene (Scene): The simulation scene containing all entities.
            source_path (str): Path or identifier of the data source / scenario.
            duration (float): Total simulation duration in seconds.
        """
        self.scene = scene
        self.duration = duration
        self.source_path = source_path

        # Simulation results collected during execution
        # - trajectory: list of (x, y) positions of the ego vehicle
        # - collisions: list of collision pairs encountered during simulation
        self.results = {"trajectory": [], "collisions": []}

    def run(self):
        """
        Run the simulation once using the current scene configuration.

        The method:
        1. Advances the scene for a fixed number of time steps.
        2. Records the ego vehicle trajectory at each step.
        3. Collects all collision events involving the ego vehicle.
        4. Deduplicates collision pairs at the end of the rollout.
        """
        steps = int(self.duration / self.scene.dt)

        for _ in range(steps):
            self.scene.step()

            # Record ego position after each simulation step
            ego = self.scene.ego
            self.results["trajectory"].append((ego.x, ego.y))

            # Accumulate collision events, if any
            if self.scene.collisions:
                self.results["collisions"].extend(self.scene.collisions)

        # Remove duplicate collision pairs (order-invariant)
        self.results["collisions"] = list(
            set(tuple(sorted(p)) for p in self.results["collisions"])
        )

    def fit_ego_path(self, dt=0.2, order=3.2):
        """
        Fit a time-parameterized polynomial trajectory for the ego vehicle.

        The fitting is performed independently for x(t) and y(t) using
        least-squares polynomial regression.

        Expected trajectory format:
            trajectory = [(x0, y0), (x1, y1), ..., (xN, yN)]

        Args:
            dt (float): Time interval between consecutive trajectory points.
            order (int): Polynomial order used for trajectory fitting.

        Returns:
            dict: A dictionary describing the fitted ego trajectory:
                {
                    "poly_order": order,
                    "x_t": [...],     # Polynomial coefficients for x(t) (np.polyfit format)
                    "y_t": [...],     # Polynomial coefficients for y(t)
                    "start": (x0, y0),
                    "end": (xN, yN),
                    "duration": total_time
                }
        """
        trajectory = self.results["trajectory"]
        n = len(trajectory)

        # Ensure sufficient data points for polynomial fitting
        if n < order + 1:
            raise ValueError(
                "Insufficient trajectory points to fit the specified polynomial order"
            )

        # Construct time stamps for each trajectory point
        t = np.arange(n) * dt

        # Separate x and y coordinates
        x = np.array([p[0] for p in trajectory])
        y = np.array([p[1] for p in trajectory])

        # Polynomial fitting for x(t) and y(t)
        fx = np.polyfit(t, x, order)
        fy = np.polyfit(t, y, order)

        start = tuple(trajectory[0])
        end = tuple(trajectory[-1])
        duration = t[-1]

        return {
            "poly_order": order,
            "x_t": fx.tolist(),
            "y_t": fy.tolist(),
            "start": start,
            "end": end,
            "duration": float(duration)
        }

    def run_multiple_ego_controls(self, control_list):
        """
        Run multiple simulations with different ego control configurations.

        Each control configuration is applied independently on a deep-copied
        scene to avoid cross-run interference.

        Args:
            control_list (List[dict]): List of ego control configurations, e.g.:
                [
                    {"vx": 0, "ay": +75},
                    {"vx": 25, "ay": +150},
                    {"vx": -25, "ay": -75}
                ]

        Returns:
            list: A list of simulation results, one per control configuration.
        """
        all_runs = []

        for i, control in enumerate(control_list):
            # Deep copy the scene to ensure isolation between simulations
            local_scene = copy.deepcopy(self.scene)

            # Override ego control parameters if specified
            local_scene.ego.vx = control.get("vx", local_scene.ego.vx)
            local_scene.ego.ay = control.get("ay", local_scene.ego.ay)

            # Example debug output (disabled by default)
            # print(
            #     f"▶ Running scenario {i+1}/{len(control_list)}: "
            #     f"vx={local_scene.ego.vx}, ay={local_scene.ego.ay}"
            # )

            sim = Simulator(local_scene, self.source_path, self.duration)
            sim.run()
            sim_path_func = sim.fit_ego_path()

            all_runs.append({
                "control": control,
                "trajectory": sim.results["trajectory"],
                "collisions": sim.results["collisions"],
                "ego_path_function": sim_path_func
            })

        return all_runs

    def run_get_fun(self, control):
        """
        Run a single simulation and return only the fitted ego trajectory function.

        This is a lightweight helper method intended for scenarios where only
        the ego path representation is required.

        Args:
            control (dict): Ego control parameters (e.g., {"vx": ..., "ay": ...}).

        Returns:
            list: A list containing a single dictionary with the fitted trajectory.
        """
        result = []

        # Isolate the simulation by deep copying the scene
        local_scene = copy.deepcopy(self.scene)

        # Apply ego control overrides
        local_scene.ego.vx = control.get("vx", local_scene.ego.vx)
        local_scene.ego.ay = control.get("ay", local_scene.ego.ay)

        sim = Simulator(local_scene, self.source_path, self.duration)
        sim.run()
        sim_path_func = sim.fit_ego_path()

        result.append({
            "ego_path_function": sim_path_func
        })

        return result
