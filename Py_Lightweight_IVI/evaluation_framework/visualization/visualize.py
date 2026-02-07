import os

import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.patches import Rectangle


def plot_scene(scene, ego_trajectories=None, gt_trajectory=None, save_path=None, filename=None):
    """
    Visualize the simulation scene and optional ego trajectories.

    This function renders:
    - All entities in the scene as oriented rectangles using their corner points
    - Optional multiple ego trajectories (e.g., from different control rollouts)
    - Optional ground-truth trajectory for comparison

    Args:
        scene: Scene object containing entities and scene dimensions.
        ego_trajectories (list, optional): List of ego trajectories, where each
            trajectory is a list of (x, y) tuples.
        gt_trajectory (list, optional): Ground-truth trajectory as a list of (x, y) tuples.
        save_path (str, optional): Directory path where the visualization will be saved.
        filename (str, optional): Base filename (without extension) for the saved image.
    """

    # Create a figure and axis with a tall aspect ratio suitable for road scenes
    fig, ax = plt.subplots(figsize=(6, 12))

    # Configure scene bounds and aspect ratio
    ax.set_xlim(0, scene.width)
    ax.set_ylim(0, scene.height)
    ax.set_aspect('equal', adjustable='box')
    ax.set_title("Scene Visualization (unit-based)")

    # Draw all entities in the scene
    for e in scene.entities:
        # Retrieve the four corner points of the entity footprint
        # Format: [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
        corners = e.get_corners()

        # Color mapping by entity type
        color = {
            "ego": "orange",
            "vehicle": "blue",
            "pedestrian": "green",
            "obstacle": "gray"
        }.get(e.type, "black")

        # Draw the entity footprint using a polygon defined by its four corners
        # This supports rotated rectangles and avoids axis-aligned assumptions
        rect = patches.Polygon(
            corners,
            facecolor=color,
            alpha=0.5,
            label=e.type,
            edgecolor='black'  # Add an outline for better visual clarity
        )
        ax.add_patch(rect)

        # Draw the entity ID at its center position
        ax.text(e.x, e.y, e.id, fontsize=6, ha='center')

    # Plot ego trajectories, if provided
    if ego_trajectories:
        colors = ["red", "purple", "magenta", "brown", "cyan"]
        for i, traj in enumerate(ego_trajectories):
            xs, ys = zip(*traj)
            ax.plot(
                xs,
                ys,
                color=colors[i % len(colors)],
                lw=2,
                label=f"ego path {i + 1}"
            )

    # Plot ground-truth trajectory, if provided
    if gt_trajectory:
        xs, ys = zip(*gt_trajectory)
        ax.plot(
            xs,
            ys,
            color='black',
            lw=2.5,
            linestyle='--',
            label="ground truth"
        )

    # Final plot styling
    ax.legend(loc='upper right', fontsize=7)
    ax.grid(True, linestyle='--', alpha=0.3)

    # Save the visualization to disk
    os.makedirs(save_path, exist_ok=True)
    save_path_1 = os.path.join(save_path, f"{filename}_scene.png")
    plt.savefig(save_path_1, dpi=200)

    # Display the figure interactively
    plt.show()
