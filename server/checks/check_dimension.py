def check_image_dimensions(image, target_width=1200, target_height=1200):
    """
    Check if the image has the specified dimensions.
    
    Args:
        image (PIL.Image): Already opened PIL image
        target_width (int): Expected width in pixels (default: 1200)
        target_height (int): Expected height in pixels (default: 1200)
    
    Returns:
        bool: True if image dimensions match target dimensions, False otherwise
    """
    if image is None:
        return False
    
    # Get actual image dimensions
    actual_width, actual_height = image.size
    
    # Check if dimensions match exactly
    return actual_width == target_width and actual_height == target_height