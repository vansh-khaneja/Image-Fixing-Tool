import cv2
import numpy as np
import math
from PIL import Image, ImageDraw

def auto_determine_grid(num_objects, image_width=None, image_height=None):
    """
    Automatically determine optimal grid size based on number of objects
    """
    if num_objects <= 0:
        return 1, 1
    elif num_objects == 1:
        return 1, 1
    elif num_objects == 2:
        return 1, 2
    elif num_objects <= 4:
        return 2, 2
    elif num_objects <= 6:
        return 2, 3
    elif num_objects <= 9:
        return 3, 3
    elif num_objects <= 12:
        return 3, 4
    elif num_objects <= 16:
        return 4, 4
    else:
        # For larger numbers, create near-square grids
        sqrt_n = math.sqrt(num_objects)
        rows = math.ceil(sqrt_n)
        cols = math.ceil(num_objects / rows)
        return rows, cols

def get_box_center(start_x, start_y, end_x, end_y):
    center_x = (start_x + end_x) // 2
    center_y = (start_y + end_y) // 2
    return center_x, center_y

def is_near_center(image_path, x, y, threshold=50):
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        return False
    
    height, width = img.shape[:2]
    
    # Calculate center
    center_x = width // 2
    center_y = height // 2
    
    # Calculate distance from center
    distance_x = abs(x - center_x)
    distance_y = abs(y - center_y)
    
    # Check if within threshold
    return distance_x <= threshold and distance_y <= threshold

def match_boxes_to_grid(image_path, box_coordinates, center_threshold=None):

    # Load image to get dimensions
    img = cv2.imread(image_path)
    if img is None:
        return []
    
    height, width = img.shape[:2]
    
    # Filter out None values and count valid objects
    valid_centroids = [c for c in box_coordinates if c is not None]
    num_objects = len(valid_centroids)
    
    # AUTOMATICALLY determine grid size
    grid_rows, grid_cols = auto_determine_grid(num_objects, width, height)
    
    print(f"Auto-detected grid: {grid_rows}x{grid_cols} for {num_objects} objects")
    
    # Calculate grid cell dimensions
    cell_width = width // grid_cols
    cell_height = height // grid_rows
    
    # Calculate grid cell centers
    grid_cell_centers = []
    for row in range(grid_rows):
        for col in range(grid_cols):
            center_x = (col * cell_width) + (cell_width // 2)
            center_y = (row * cell_height) + (cell_height // 2)
            grid_cell_centers.append((center_x, center_y, row, col))
    
    # Create result array with None values
    ordered_centers = [None] * (grid_rows * grid_cols)
    center_checks = [None] * (grid_rows * grid_cols)
    
    # For each detected centroid, find the closest grid cell
    used_positions = set()
    
    for centroid in valid_centroids:
        center_x, center_y = centroid
        best_distance = float('inf')
        best_position = None
        best_grid_center = None
        
        # Find closest grid cell that hasn't been used
        for i, (grid_x, grid_y, row, col) in enumerate(grid_cell_centers):
            if i in used_positions:
                continue
                
            distance = ((center_x - grid_x)**2 + (center_y - grid_y)**2)**0.5
            
            if distance < best_distance:
                best_distance = distance
                best_position = i
                best_grid_center = (grid_x, grid_y)
        
        # Assign to best position
        if best_position is not None:
            ordered_centers[best_position] = (center_x, center_y)
            used_positions.add(best_position)
            
            # Check if centered if threshold provided
            if center_threshold is not None:
                grid_x, grid_y = best_grid_center
                distance_x = abs(center_x - grid_x)
                distance_y = abs(center_y - grid_y)
                is_centered = distance_x <= center_threshold and distance_y <= center_threshold
                center_checks[best_position] = is_centered
    
    # Return based on whether threshold was used
    if center_threshold is not None:
        return {
            'centers': ordered_centers,
            'is_centered': center_checks,
            'grid_info': {
                'cell_width': cell_width,
                'cell_height': cell_height,
                'threshold': center_threshold,
                'grid_rows': grid_rows,
                'grid_cols': grid_cols
            }
        }
    else:
        return ordered_centers

