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
        return 1, 2  # Horizontal layout for 2 objects
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
    
    # Get image dimensions
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
    """
    Match detected box centroids to grid positions - AUTOMATICALLY determines grid size!
    
    Args:
        image_path (str): Path to the image
        box_coordinates (list): List of (center_x, center_y) tuples
        center_threshold (int): Optional threshold for checking if boxes are centered in cells
    
    Returns:
        list or dict: Ordered list of centroids or dict with additional info if threshold provided
    """
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

def arrange_bounding_boxes_in_grid(image, bounding_boxes, spacing_factor=1.0, spacing_mode="auto", maintain_aspect_ratio=True):
    """
    Arrange bounding boxes in a grid layout - AUTOMATICALLY determines grid size!
    """
    if not bounding_boxes:
        return []
    
    img_width, img_height = image.size
    num_boxes = len(bounding_boxes)
    
    # AUTOMATICALLY determine grid size
    grid_rows, grid_cols = auto_determine_grid(num_boxes, img_width, img_height)
    
    print(f"Auto-arranged grid: {grid_rows}x{grid_cols} for {num_boxes} boxes")
    
    # Calculate original box dimensions
    original_boxes = []
    for x1, y1, x2, y2 in bounding_boxes:
        width = x2 - x1
        height = y2 - y1
        original_boxes.append((width, height))
    
    # Intelligent spacing calculation based on mode and number of boxes
    def get_spacing_params(mode, num_boxes, img_width, img_height):
        base_size = min(img_width, img_height)
        
        if mode == "minimal":
            base_padding = base_size * 0.01
            base_spacing = base_size * 0.015
        elif mode == "tight":
            base_padding = base_size * 0.015
            base_spacing = base_size * 0.02
        elif mode == "balanced":
            base_padding = base_size * 0.025
            base_spacing = base_size * 0.035
        elif mode == "generous":
            base_padding = base_size * 0.04
            base_spacing = base_size * 0.06
        else:  # auto mode
            if num_boxes <= 2:
                base_padding = base_size * 0.05
                base_spacing = base_size * 0.08
            elif num_boxes <= 4:
                base_padding = base_size * 0.03
                base_spacing = base_size * 0.05
            elif num_boxes <= 9:
                base_padding = base_size * 0.02
                base_spacing = base_size * 0.03
            elif num_boxes <= 16:
                base_padding = base_size * 0.015
                base_spacing = base_size * 0.02
            else:
                base_padding = base_size * 0.01
                base_spacing = base_size * 0.015
        
        return base_padding, base_spacing
    
    base_padding, base_item_spacing = get_spacing_params(spacing_mode, num_boxes, img_width, img_height)
    
    # Apply spacing factor
    padding = int(base_padding * spacing_factor)
    item_spacing = int(base_item_spacing * spacing_factor)
    
    # Ensure minimum spacing
    padding = max(5, padding)
    item_spacing = max(5, item_spacing)
    
    # Calculate available space for each grid cell (accounting for item spacing)
    total_horizontal_spacing = padding * 2 + item_spacing * (grid_cols - 1)
    total_vertical_spacing = padding * 2 + item_spacing * (grid_rows - 1)
    
    available_width = (img_width - total_horizontal_spacing) // grid_cols
    available_height = (img_height - total_vertical_spacing) // grid_rows
    
    # Ensure we have positive dimensions
    available_width = max(10, available_width)
    available_height = max(10, available_height)
    
    new_bounding_boxes = []
    
    for i, (orig_width, orig_height) in enumerate(original_boxes):
        # Calculate grid position
        row = i // grid_cols
        col = i % grid_cols
        
        # Check if this is the last row and has fewer items than grid_cols
        items_in_current_row = min(grid_cols, num_boxes - row * grid_cols)
        
        if items_in_current_row < grid_cols:
            # Center the items in the last row
            row_offset = (grid_cols - items_in_current_row) * (available_width + item_spacing) // 2
            cell_x = padding + row_offset + col * (available_width + item_spacing)
        else:
            # Normal positioning for full rows
            cell_x = padding + col * (available_width + item_spacing)
        
        cell_y = padding + row * (available_height + item_spacing)
        
        if maintain_aspect_ratio:
            # Scale to fit while maintaining aspect ratio
            scale_x = available_width / orig_width
            scale_y = available_height / orig_height
            scale = min(scale_x, scale_y)
            
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
            
            # Center in cell
            x_offset = (available_width - new_width) // 2
            y_offset = (available_height - new_height) // 2
            
            x1 = cell_x + x_offset
            y1 = cell_y + y_offset
            x2 = x1 + new_width
            y2 = y1 + new_height
        else:
            # Stretch to fill cell
            x1 = cell_x
            y1 = cell_y
            x2 = cell_x + available_width
            y2 = cell_y + available_height
        
        new_bounding_boxes.append((x1, y1, x2, y2))
    
    return new_bounding_boxes

def rearrange_image_content(image, original_boxes, background_color=(255, 255, 255), spacing_factor=1.0, spacing_mode="auto", save_path=None, check_result=False):
    """
    Crop regions from original bounding boxes and arrange them in a grid layout.
    Grid size is AUTOMATICALLY determined!
    """
    if check_result == True:
        print("Check Result is True, skipping rearrangement")
        return image
    
    if not original_boxes:
        return image
    
    # Get new arranged positions with automatic grid sizing
    new_boxes = arrange_bounding_boxes_in_grid(image, original_boxes, spacing_factor=spacing_factor, spacing_mode=spacing_mode)
    
    # Create new image with same size as original
    new_image = Image.new(image.mode, image.size, background_color)
    
    # Crop original regions and paste them in new positions
    for i, ((orig_x1, orig_y1, orig_x2, orig_y2), (new_x1, new_y1, new_x2, new_y2)) in enumerate(zip(original_boxes, new_boxes)):
        # Crop the region from original image
        cropped_region = image.crop((orig_x1, orig_y1, orig_x2, orig_y2))
        
        # Resize cropped region to fit new box dimensions
        new_width = new_x2 - new_x1
        new_height = new_y2 - new_y1
        resized_region = cropped_region.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Paste in new position
        new_image.paste(resized_region, (new_x1, new_y1))
    
    if save_path:
        new_image.save(save_path)
        print(f"Rearranged image saved to: {save_path}")
        print(f"Spacing mode: {spacing_mode}, factor: {spacing_factor}")
        print(f"Number of boxes: {len(original_boxes)}")
    
    return new_image

def check_products_alignment(image, product_centroids, alignment_threshold=50, spacing_factor=1.0, spacing_mode="auto"):
    """
    Check if products in an already opened PIL image are aligned to their grid centers.
    Uses the SAME centering logic as arrange_bounding_boxes_in_grid function.
    
    Args:
        image (PIL.Image): Already opened PIL image
        product_centroids (list): List of (center_x, center_y) tuples for detected products
        alignment_threshold (int): Maximum distance from grid center to consider aligned (default: 50 pixels)
        spacing_factor (float): Controls overall spacing (1.0 = default, 0.5 = tighter, 2.0 = more spaced)
        spacing_mode (str): "auto", "tight", "balanced", "generous", or "minimal"
    
    Returns:
        bool: True if all products are aligned to their grid centers, False otherwise
    """
    if not product_centroids:
        return True  # No products to check
    
    # Get image dimensions
    img_width, img_height = image.size
    
    # Filter out None values and count valid objects
    valid_centroids = [c for c in product_centroids if c is not None]
    num_objects = len(valid_centroids)
    
    if num_objects == 0:
        return True
    
    # Use SAME grid determination logic as arrange_bounding_boxes_in_grid
    if num_objects == 1:
        grid_cols, grid_rows = 1, 1
    elif num_objects == 2:
        grid_cols, grid_rows = 2, 1
    elif num_objects <= 4:
        grid_cols, grid_rows = 2, 2
    elif num_objects <= 6:
        grid_cols, grid_rows = 3, 2
    elif num_objects <= 9:
        grid_cols, grid_rows = 3, 3
    elif num_objects <= 12:
        grid_cols, grid_rows = 4, 3
    elif num_objects <= 16:
        grid_cols, grid_rows = 4, 4
    else:
        # For more boxes, create a more square-like grid
        grid_cols = math.ceil(math.sqrt(num_objects))
        grid_rows = math.ceil(num_objects / grid_cols)
    
    # Use SAME spacing calculation logic
    def get_spacing_params(mode, num_boxes, img_width, img_height):
        base_size = min(img_width, img_height)
        
        if mode == "minimal":
            base_padding = base_size * 0.01
            base_spacing = base_size * 0.015
        elif mode == "tight":
            base_padding = base_size * 0.015
            base_spacing = base_size * 0.02
        elif mode == "balanced":
            base_padding = base_size * 0.025
            base_spacing = base_size * 0.035
        elif mode == "generous":
            base_padding = base_size * 0.04
            base_spacing = base_size * 0.06
        else:  # auto mode
            if num_boxes <= 2:
                base_padding = base_size * 0.05
                base_spacing = base_size * 0.08
            elif num_boxes <= 4:
                base_padding = base_size * 0.03
                base_spacing = base_size * 0.05
            elif num_boxes <= 9:
                base_padding = base_size * 0.02
                base_spacing = base_size * 0.03
            elif num_boxes <= 16:
                base_padding = base_size * 0.015
                base_spacing = base_size * 0.02
            else:
                base_padding = base_size * 0.01
                base_spacing = base_size * 0.015
        
        return base_padding, base_spacing
    
    base_padding, base_item_spacing = get_spacing_params(spacing_mode, num_objects, img_width, img_height)
    
    # Apply spacing factor
    padding = int(base_padding * spacing_factor)
    item_spacing = int(base_item_spacing * spacing_factor)
    
    # Ensure minimum spacing
    padding = max(5, padding)
    item_spacing = max(5, item_spacing)
    
    # Calculate available space for each grid cell (accounting for item spacing)
    total_horizontal_spacing = padding * 2 + item_spacing * (grid_cols - 1)
    total_vertical_spacing = padding * 2 + item_spacing * (grid_rows - 1)
    
    available_width = (img_width - total_horizontal_spacing) // grid_cols
    available_height = (img_height - total_vertical_spacing) // grid_rows
    
    # Ensure we have positive dimensions
    available_width = max(10, available_width)
    available_height = max(10, available_height)
    
    # Calculate expected grid centers using SAME logic as arrange_bounding_boxes_in_grid
    expected_centers = []
    
    for i in range(num_objects):
        # Calculate grid position
        row = i // grid_cols
        col = i % grid_cols
        
        # Check if this is the last row and has fewer items than grid_cols
        items_in_current_row = min(grid_cols, num_objects - row * grid_cols)
        
        if items_in_current_row < grid_cols:
            # Center the items in the last row (SAME LOGIC!)
            row_offset = (grid_cols - items_in_current_row) * (available_width + item_spacing) // 2
            cell_x = padding + row_offset + col * (available_width + item_spacing)
        else:
            # Normal positioning for full rows
            cell_x = padding + col * (available_width + item_spacing)
        
        cell_y = padding + row * (available_height + item_spacing)
        
        # Calculate center of this cell
        center_x = cell_x + (available_width // 2)
        center_y = cell_y + (available_height // 2)
        
        expected_centers.append((center_x, center_y))
    
    # For each product centroid, find the closest expected center and check distance
    used_positions = set()
    
    for centroid in valid_centroids:
        center_x, center_y = centroid
        best_distance = float('inf')
        best_position = None
        
        # Find closest expected center that hasn't been used
        for i, (expected_x, expected_y) in enumerate(expected_centers):
            if i in used_positions:
                continue
                
            distance = ((center_x - expected_x)**2 + (center_y - expected_y)**2)**0.5
            
            if distance < best_distance:
                best_distance = distance
                best_position = i
        
        # Check if this product is aligned (within threshold)
        if best_distance > alignment_threshold:
            return False  # Product is not aligned
            
        # Mark this grid position as used
        if best_position is not None:
            used_positions.add(best_position)
    
    return True  # All products are aligned