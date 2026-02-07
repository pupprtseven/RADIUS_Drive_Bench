import numpy as np
import json


def compute_fit_score(fit_func, ground_truth, dt=0.2):
    """
    Compute the similarity score between a fitted trajectory and the ground-truth trajectory.

    The similarity is evaluated based on the mean squared Euclidean distance
    between corresponding points along the two trajectories. A smaller distance
    indicates better alignment. The final score is mapped to (0, 1] using an
    exponential decay function.

    Args:
        fit_func (dict): A dictionary describing the fitted trajectory function, containing:
            - "x_t": Polynomial coefficients for x(t) (NumPy polyfit format).
            - "y_t": Polynomial coefficients for y(t) (NumPy polyfit format).
            - "duration": Total trajectory duration.
        ground_truth (list): Ground-truth trajectory represented as a list of (x, y) tuples.
        dt (float): Time interval between consecutive trajectory points.

    Returns:
        float or None: A scalar fit score in (0, 1], where higher values indicate
        better alignment with the ground truth. Returns None if ground_truth is empty.
    """
    # If no ground-truth trajectory is provided, the fit score is undefined
    if not ground_truth:
        return None

    # Construct polynomial functions x(t) and y(t) from fitted coefficients
    fx = np.poly1d(fit_func["x_t"])
    fy = np.poly1d(fit_func["y_t"])

    # Number of ground-truth trajectory points
    n = len(ground_truth)

    # Generate corresponding time stamps
    t = np.arange(n) * dt

    # Convert ground-truth trajectory to NumPy array
    gt = np.array(ground_truth)

    # Evaluate fitted trajectory at the same time stamps
    pred = np.stack([fx(t), fy(t)], axis=1)

    # Compute per-point Euclidean distance between prediction and ground truth
    dist = np.linalg.norm(pred - gt, axis=1)

    # Mean squared error over the trajectory
    mse = np.mean(dist ** 2)

    # Convert error to a normalized similarity score using exponential decay
    # Smaller MSE leads to a higher score (closer to 1)
    score = float(np.exp(-mse / 1e4))

    return score
