import math
from PIL import Image, ImageDraw

def arrange_bounding_boxes_in_grid(image, bounding_boxes, spacing_factor=1.0, spacing_mode="auto", maintain_aspect_ratio=True):
    """
    Arrange bounding boxes in a grid layout with intelligent spacing adjustment.
    
    Args:
        image: PIL Image object
        bounding_boxes: List of tuples [(x1, y1, x2, y2), ...]
        spacing_factor: Controls overall spacing (1.0 = default, 0.5 = tighter, 2.0 = more spaced)
        spacing_mode: "auto", "tight", "balanced", "generous", or "minimal"
        maintain_aspect_ratio: Whether to maintain original aspect ratios of boxes
    
    Returns:
        List of new bounding box coordinates arranged in grid
    """
    if not bounding_boxes:
        return []
    
    img_width, img_height = image.size
    num_boxes = len(bounding_boxes)
    
    # Calculate original box dimensions
    original_boxes = []
    for x1, y1, x2, y2 in bounding_boxes:
        width = x2 - x1
        height = y2 - y1
        original_boxes.append((width, height))
    
    # Determine grid layout
    if num_boxes == 1:
        grid_cols, grid_rows = 1, 1
    elif num_boxes == 2:
        grid_cols, grid_rows = 2, 1
    elif num_boxes <= 4:
        grid_cols, grid_rows = 2, 2
    elif num_boxes <= 6:
        grid_cols, grid_rows = 3, 2
    elif num_boxes <= 9:
        grid_cols, grid_rows = 3, 3
    elif num_boxes <= 12:
        grid_cols, grid_rows = 4, 3
    elif num_boxes <= 16:
        grid_cols, grid_rows = 4, 4
    else:
        # For more boxes, create a more square-like grid
        grid_cols = math.ceil(math.sqrt(num_boxes))
        grid_rows = math.ceil(num_boxes / grid_cols)
    
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

def rearrange_image_content(image, original_boxes, background_color=(255, 255, 255), spacing_factor=1.0, spacing_mode="auto", save_path=None,check_result=False):
    """
    Crop regions from original bounding boxes and arrange them in a grid layout.
    
    Args:
        image: PIL Image object
        original_boxes: List of original bounding boxes to crop
        background_color: Background color for the new image (default: white)
        spacing_factor: Controls overall spacing (1.0 = default, 0.5 = tighter, 2.0 = more spaced)
        spacing_mode: "auto", "tight", "balanced", "generous", or "minimal"
        save_path: Path to save the rearranged image
    
    Returns:
        PIL Image with cropped regions arranged in grid
    """
    if check_result==True:
        print("Check Result is True, skipping rearrangement")
        return image
    
    
    if not original_boxes:
        return image
    
    # Get new arranged positions with intelligent spacing
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

def visualize_bounding_boxes(image, original_boxes, new_boxes=None, spacing_factor=1.0, save_path=None):
    """
    Visualize original and new bounding boxes on the image.
    
    Args:
        image: PIL Image object
        original_boxes: List of original bounding boxes
        new_boxes: List of new arranged bounding boxes (auto-calculated if None)
        spacing_factor: Spacing factor for auto-calculation
        save_path: Optional path to save the visualization
    """
    if new_boxes is None:
        new_boxes = arrange_bounding_boxes_in_grid(image, original_boxes, spacing_factor=spacing_factor)
    
    # Create a copy of the image for visualization
    vis_image = image.copy()
    draw = ImageDraw.Draw(vis_image)
    
    # Draw original boxes in red
    for i, (x1, y1, x2, y2) in enumerate(original_boxes):
        draw.rectangle([x1, y1, x2, y2], outline='red', width=2)
        draw.text((x1, y1-15), f'Orig {i+1}', fill='red')
    
    # Draw new boxes in green
    for i, (x1, y1, x2, y2) in enumerate(new_boxes):
        draw.rectangle([x1, y1, x2, y2], outline='green', width=2)
        draw.text((x1, y1-15), f'New {i+1}', fill='green')
    
    if save_path:
        vis_image.save(save_path)
    
    return vis_image

# Complete workflow functions
def process_and_save_rearranged_image(image, original_boxes, output_path, background_color=(255, 255, 255), spacing_factor=1.0, spacing_mode="auto"):
    """
    Complete workflow: crop, arrange, and save the rearranged image with intelligent spacing.
    
    Args:
        image: PIL Image object
        original_boxes: List of bounding boxes [(x1, y1, x2, y2), ...]
        output_path: Path where to save the final image
        background_color: Background color for empty areas
        spacing_factor: Controls overall spacing (1.0 = default, 0.5 = tighter, 2.0 = more spaced)
        spacing_mode: "auto", "tight", "balanced", "generous", or "minimal"
    
    Returns:
        PIL Image object of the rearranged image
    """
    # Create the rearranged image with intelligent spacing
    rearranged_image = rearrange_image_content(
        image, 
        original_boxes, 
        background_color=background_color,
        spacing_factor=spacing_factor,
        spacing_mode=spacing_mode,
        save_path=output_path
    )
    
    return rearranged_image

# Example usage:
def example_usage():
    """
    Example of how to use the image rearrangement function.
    """
    # Load your PIL image
    # image = Image.open('your_image.jpg')
    
    # Your bounding boxes
    original_bboxes = [
        (100, 100, 300, 200),  # Box 1
        (400, 150, 600, 300),  # Box 2
        (200, 350, 350, 450),  # Box 3
        (500, 400, 700, 550),  # Box 4
    ]
    
    # AUTOMATED SPACING - Just use one parameter!
    
    # Method 1: Default spacing (automatically adjusts for number of boxes)
    # rearranged_img = rearrange_image_content(image, original_bboxes, save_path='rearranged.jpg')
    
    # Method 2: Tighter spacing (good for many boxes)
    # rearranged_img = rearrange_image_content(
    #     image, original_bboxes, 
    #     spacing_factor=0.5,  # Tighter spacing
    #     save_path='tight_layout.jpg'
    # )
    
    # Method 3: More generous spacing (good for few boxes)
    # rearranged_img = rearrange_image_content(
    #     image, original_bboxes, 
    #     spacing_factor=1.5,  # More spacing
    #     save_path='spaced_layout.jpg'
    # )
    
    # Method 4: Complete workflow
    # final_img = process_and_save_rearranged_image(
    #     image, 
    #     original_bboxes, 
    #     'final_image.jpg',
    #     spacing_factor=1.2  # Slightly more spaced
    # )
    
    # Method 3: Create visualization showing before/after
    # new_bboxes = arrange_bounding_boxes_in_grid(image, original_bboxes)
    # visualization = visualize_bounding_boxes(image, original_bboxes, new_bboxes, 'bbox_visualization.jpg')
    
    print("Image rearrangement completed!")
    print("Original boxes:", original_bboxes)

# Advanced version with custom grid specification
def arrange_bounding_boxes_custom_grid(image, bounding_boxes, grid_cols=None, grid_rows=None, spacing_factor=1.0):
    """
    Arrange bounding boxes with custom grid specification.
    
    Args:
        image: PIL Image object
        bounding_boxes: List of tuples [(x1, y1, x2, y2), ...]
        grid_cols: Number of columns (optional)
        grid_rows: Number of rows (optional)
        spacing_factor: Controls overall spacing
    """
    if not bounding_boxes:
        return []
    
    num_boxes = len(bounding_boxes)
    
    # If grid dimensions not specified, calculate optimal grid
    if grid_cols is None or grid_rows is None:
        if num_boxes == 1:
            grid_cols, grid_rows = 1, 1
        elif num_boxes == 2:
            grid_cols, grid_rows = 2, 1
        else:
            grid_cols = math.ceil(math.sqrt(num_boxes))
            grid_rows = math.ceil(num_boxes / grid_cols)
    
    # Ensure grid can accommodate all boxes
    while grid_cols * grid_rows < num_boxes:
        grid_rows += 1
    
    img_width, img_height = image.size
    
    # Auto-calculate spacing
    base_padding = min(img_width, img_height) * 0.02
    base_item_spacing = min(img_width, img_height) * 0.03
    spacing_reduction = max(0.3, 1.0 - (num_boxes - 1) * 0.1)
    
    padding = int(base_padding * spacing_factor * spacing_reduction)
    item_spacing = int(base_item_spacing * spacing_factor * spacing_reduction)
    
    padding = max(5, padding)
    item_spacing = max(5, item_spacing)
    
    # Calculate cell dimensions (with item spacing)
    total_horizontal_spacing = padding * 2 + item_spacing * (grid_cols - 1)
    total_vertical_spacing = padding * 2 + item_spacing * (grid_rows - 1)
    
    cell_width = (img_width - total_horizontal_spacing) // grid_cols
    cell_height = (img_height - total_vertical_spacing) // grid_rows
    
    new_boxes = []
    
    for i in range(num_boxes):
        row = i // grid_cols
        col = i % grid_cols
        
        # Check if this is the last row and has fewer items than grid_cols
        items_in_current_row = min(grid_cols, num_boxes - row * grid_cols)
        
        if items_in_current_row < grid_cols:
            # Center the items in the last row
            row_offset = (grid_cols - items_in_current_row) * (cell_width + item_spacing) // 2
            x1 = padding + row_offset + col * (cell_width + item_spacing)
        else:
            # Normal positioning for full rows
            x1 = padding + col * (cell_width + item_spacing)
        
        y1 = padding + row * (cell_height + item_spacing)
        x2 = x1 + cell_width
        y2 = y1 + cell_height
        
        new_boxes.append((x1, y1, x2, y2))
    
    return new_boxes

# if __name__ == "__main__":
#     example_usage()