from typing import List
from Py_Lightweight_IVI.evaluation_framework.core.entitys import Entity, Vehicle, Pedestrian, StaticObstacle
from Py_Lightweight_IVI.evaluation_framework.utils.geometry import check_collision


class Scene:
    """
    Scene class that encapsulates all entities and the global simulation state.

    The Scene is responsible for:
    - Maintaining the list of all entities (vehicles, pedestrians, obstacles, etc.)
    - Advancing the simulation in discrete time steps
    - Detecting and recording collisions between entities
    - Tracking global simulation time
    """

    def __init__(self, width=1000, height=2000, dt=0.2):
        """
        Initialize a simulation scene.

        Args:
            width (float): Width of the scene boundary (e.g., road extent in x-axis).
            height (float): Height of the scene boundary (e.g., road extent in y-axis).
            dt (float): Simulation time step in seconds.
        """
        self.width = width
        self.height = height
        self.dt = dt

        # List of all entities participating in the scene
        self.entities: List[Entity] = []

        # Global simulation time (in seconds)
        self.time = 0.0

        # List of collision pairs detected at the current time step
        # Each element is a tuple of (entity_id_1, entity_id_2)
        self.collisions = []

        # Reference to the ego vehicle, if present in the scene
        self.ego: Vehicle = None

    def add_entity(self, entity: Entity):
        """
        Add an entity to the scene.

        If the entity is marked as the ego vehicle, a direct reference
        is stored for fast access.

        Args:
            entity (Entity): The entity instance to be added to the scene.
        """
        self.entities.append(entity)

        # Identify and store the ego vehicle explicitly
        if entity.type == "ego":
            self.ego = entity

    def step(self):
        """
        Advance the simulation by one time step.

        This method performs the following operations in order:
        1. Update the state of all entities using the fixed time step.
        2. Detect collisions between entities after the update.
        3. Advance the global simulation clock.
        """
        # Update all entities (both dynamic and static entities may implement update)
        for e in self.entities:
            e.update(self.dt)

        # Perform collision detection after all entities have been updated
        self.collisions = self.detect_collisions()

        # Advance simulation time
        self.time += self.dt

    def detect_collisions(self) -> List[tuple]:
        """
        Detect collisions between all pairs of entities in the scene.

        Collision checking is performed pairwise using inflated bounding boxes.
        Only collisions involving the ego vehicle are recorded; collisions
        between non-ego entities are ignored.

        Returns:
            List[tuple]: A list of collision pairs, where each pair is represented
                         as (entity_id_1, entity_id_2).
        """
        pairs = []

        # Iterate over all unique unordered pairs of entities
        for i in range(len(self.entities)):
            for j in range(i + 1, len(self.entities)):
                e1, e2 = self.entities[i], self.entities[j]

                # Check geometric collision using inflated corner representations
                if check_collision(
                    e1.get_inflated_corners(),
                    e2.get_inflated_corners()
                ):
                    # Ignore collisions that do not involve the ego vehicle
                    if not (e1.type == "ego" or e2.type == "ego"):
                        continue
                    else:
                        pairs.append((e1.id, e2.id))

        return pairs

    def to_json(self):
        """
        Serialize the current scene state into a JSON-compatible dictionary.

        The output includes:
        - Current simulation time
        - Serialized representations of all entities
        - Collision pairs detected at the current time step

        Returns:
            dict: JSON-serializable dictionary representing the scene state.
        """
        return {
            "time": self.time,
            "entities": [e.to_dict() for e in self.entities],
            "collisions": self.collisions
        }
