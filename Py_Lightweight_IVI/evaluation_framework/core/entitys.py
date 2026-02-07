import math
from typing import List, Tuple


class Entity:
    """
    Base class for all entities in the scene.

    This class represents a generic physical entity with:
    - Spatial properties (position and geometric dimensions)
    - Kinematic properties (velocity and acceleration)
    - Safety-related attributes (inflation margin)
    - A dynamic/static flag to indicate whether the entity can move

    Attributes
    ----------
    id : str
        Unique identifier of the entity.
    type : str
        Entity type, e.g., "ego", "vehicle", "pedestrian", "obstacle", "bike".
    x : float
        X-coordinate of the entity center (unit).
    y : float
        Y-coordinate of the entity center (unit).
    width : float
        Width of the entity's bounding box (unit).
    length : float
        Length of the entity's bounding box (unit).
    vx : float
        Velocity along the x-axis (unit/s).
    vy : float
        Velocity along the y-axis (unit/s).
    ay : float
        Acceleration along the y-axis (unit/s²).
    safety_margin : float
        Safety inflation margin added around the bounding box (unit).
    is_dynamic : bool
        Whether the entity is dynamic (i.e., subject to motion updates).
    """

    def __init__(
        self,
        eid: str,
        etype: str,
        x: float,
        y: float,
        width: float,
        length: float,
        vx: float = 0.0,
        vy: float = 0.0,
        ay: float = 0.0,
        safety_margin: float = 8.0,
        is_dynamic: bool = True,
    ):
        self.id = eid
        self.type = etype
        self.x = x
        self.y = y
        self.width = width
        self.length = length
        self.vx = vx
        self.vy = vy
        self.ay = ay
        self.safety_margin = safety_margin
        self.is_dynamic = is_dynamic

    # ---------------- Geometry ----------------
    def get_corners(self) -> List[Tuple[float, float]]:
        """
        Return the four corner coordinates of the axis-aligned bounding box
        without applying the safety inflation margin.

        Returns
        -------
        List[Tuple[float, float]]
            A list of four (x, y) tuples representing the rectangle corners.
        """
        half_w = self.width / 2
        half_l = self.length / 2
        return [
            (self.x - half_w, self.y - half_l),
            (self.x - half_w, self.y + half_l),
            (self.x + half_w, self.y + half_l),
            (self.x + half_w, self.y - half_l),
        ]

    def get_inflated_corners(self) -> List[Tuple[float, float]]:
        """
        Return the four corner coordinates of the bounding box after
        inflating it by the safety margin.

        The safety margin is applied uniformly in both width and length
        directions to form a conservative collision boundary.

        Returns
        -------
        List[Tuple[float, float]]
            A list of four (x, y) tuples representing the inflated rectangle corners.
        """
        half_w = (self.width / 2) + self.safety_margin
        half_l = (self.length / 2) + self.safety_margin
        return [
            (self.x - half_w, self.y - half_l),
            (self.x - half_w, self.y + half_l),
            (self.x + half_w, self.y + half_l),
            (self.x + half_w, self.y - half_l),
        ]

    # ---------------- Update ----------------
    def update(self, dt: float):
        """
        Update the entity's velocity and position over a time step.

        The update logic focuses on longitudinal motion along the y-axis.
        When vy is zero, acceleration is only applied if it is capable of
        initiating motion. Otherwise, the entity remains stationary.

        Parameters
        ----------
        dt : float
            Time step duration.
        """
        if not self.is_dynamic:
            return

        # Core logic:
        # When vy == 0, check whether ay can initiate motion.
        # If ay == 0, velocity remains zero and no update is applied.
        if self.vy == 0:
            if self.ay == 0:
                pass  # vy remains zero
            else:
                if self.ay > 0:
                    self.vy += self.ay * dt  # Start motion if acceleration is positive
                else:
                    self.vx = 0
                    pass
        else:
            if self.type == "ego":
                # Prevent ego vehicle from reversing into negative velocity
                if self.vy + self.ay * dt < 0:
                    self.vy = 0
                    self.vx = 0
                else:
                    self.vy += self.ay * dt

        # Update position using the current velocity
        self.x += self.vx * dt
        self.y += self.vy * dt

    # ---------------- Serialization ----------------
    def to_dict(self):
        """
        Serialize the entity into a dictionary representation.

        Returns
        -------
        dict
            Dictionary containing all relevant entity attributes.
        """
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "length": self.length,
            "vx": self.vx,
            "vy": self.vy,
            "ax": self.ay,
            "safety_margin": self.safety_margin,
            "is_dynamic": self.is_dynamic,
        }

    @classmethod
    def from_json(cls, data: dict):
        """
        Construct an Entity instance from a JSON-like dictionary.

        Parameters
        ----------
        data : dict
            Dictionary containing serialized entity attributes.

        Returns
        -------
        Entity
            A reconstructed Entity object.
        """
        return cls(
            eid=data["id"],
            etype=data["type"],
            x=data["x"],
            y=data["y"],
            width=data["width"],
            length=data["length"],
            vx=data.get("vx", 0.0),
            vy=data.get("vy", 0.0),
            ay=data.get("ay", 0.0),
            safety_margin=data.get("safety_margin", 8.0),
            is_dynamic=data.get("is_dynamic", True),
        )


class Vehicle(Entity):
    """
    Vehicle entity class, representing both ego vehicles and other vehicles.

    This class extends Entity by introducing:
    - Discrete acceleration modes
    - Vehicle size categories
    - Orientation-dependent geometry
    """

    ACCEL_MAP_PLUS = {"Z": 0, "A": 75.0, "B": 150.0, "C": 225.0}
    ACCEL_MAP_MINUS = {"Z": 0, "A": -75.0, "B": -150.0, "C": -300.0}

    def __init__(
        self,
        eid: str,
        etype: str,
        toward: str,
        size: str,
        x: float,
        y: float,
        vx: float,
        vy: float,
        ay: float,
        accel_mode: str = "Z",
        safety_margin: float = 8.0,
    ):
        self.size = size
        self.toward = toward

        # Determine vehicle geometry based on size category
        if size == "Big":
            width, length = 130, 400
        elif size == "Small":
            width, length = 90, 230
        elif size == "Nm":
            width, length = 35, 90
        else:
            raise ValueError(f"Unknown vehicle size: {size}")

        # Swap width and length if orientation indicates rotation
        if toward == "1":
            width, length = length, width

        super().__init__(
            eid=eid,
            etype=etype,
            x=x,
            y=y,
            width=width,
            length=length,
            vx=vx,
            vy=vy,
            ay=ay,
            safety_margin=safety_margin,
            is_dynamic=True,
        )

        self.accel_mode = accel_mode

    def apply_acceleration(self, direction: str):
        """
        Apply acceleration or deceleration based on the given direction.

        Parameters
        ----------
        direction : str
            '+' for acceleration, '-' for deceleration.
        """
        if direction == "+":
            self.ay = self.ACCEL_MAP_PLUS[self.accel_mode]
        else:
            self.ay = self.ACCEL_MAP_MINUS[self.accel_mode]

    @classmethod
    def from_json(cls, data: dict):
        """
        Construct a Vehicle instance from a JSON-like dictionary.

        Parameters
        ----------
        data : dict
            Dictionary containing serialized vehicle attributes.

        Returns
        -------
        Vehicle
            A reconstructed Vehicle object.
        """
        return cls(
            eid=data["id"],
            etype=data["type"],
            toward=data["toward"],
            size=data["size"],
            x=data["x"],
            y=data["y"],
            vx=data.get("vx", 0.0),
            vy=data.get("vy", 0.0),
            ay=data.get("ay", 0.0),
            accel_mode=data.get("accel_mode", "Z"),
            safety_margin=data.get("safety_margin", 8.0),
        )


class Pedestrian(Entity):
    """
    Pedestrian entity class.

    Pedestrians are modeled as small dynamic entities with fixed geometry
    and typically lower safety margins compared to vehicles.
    """

    def __init__(
        self,
        eid: str,
        x: float,
        y: float,
        vx: float,
        vy: float,
        safety_margin: float = 15.0,
    ):
        super().__init__(
            eid,
            "pedestrian",
            x,
            y,
            30,
            30,
            vx,
            vy,
            0.0,
            safety_margin,
            True,
        )

    @classmethod
    def from_json(cls, data: dict):
        """
        Construct a Pedestrian instance from a JSON-like dictionary.

        Parameters
        ----------
        data : dict
            Dictionary containing serialized pedestrian attributes.

        Returns
        -------
        Pedestrian
            A reconstructed Pedestrian object.
        """
        return cls(
            eid=data["id"],
            x=data["x"],
            y=data["y"],
            vx=data.get("vx", 0.0),
            vy=data.get("vy", 0.0),
            safety_margin=data.get("safety_margin", 15.0),
        )


class StaticObstacle(Entity):
    """
    Static obstacle entity class.

    Static obstacles do not move and are excluded from kinematic updates.
    """

    def __init__(
        self,
        eid: str,
        x: float,
        y: float,
        width: float,
        length: float,
        safety_margin: float = 8.0,
    ):
        super().__init__(
            eid,
            "obstacle",
            x,
            y,
            width,
            length,
            0.0,
            0.0,
            0.0,
            safety_margin,
            False,
        )

    @classmethod
    def from_json(cls, data: dict):
        """
        Construct a StaticObstacle instance from a JSON-like dictionary.

        Parameters
        ----------
        data : dict
            Dictionary containing serialized obstacle attributes.

        Returns
        -------
        StaticObstacle
            A reconstructed StaticObstacle object.
        """
        return cls(
            eid=data["id"],
            x=data["x"],
            y=data["y"],
            width=data["width"],
            length=data["length"],
            safety_margin=data.get("safety_margin", 8.0),
        )
