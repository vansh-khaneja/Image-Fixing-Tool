from PIL import Image, ImageOps

def create_white_image(size=(1200, 1200), color=(255, 255, 255)):
    """
    Creates a white image of the specified size.
    :param size: Tuple specifying the size of the image (width, height).
    :param color: Tuple specifying the color (default is white).
    :return: A PIL Image object.
    """
    return Image.new("RGB", size, color)

def resize_image_proportionally(image, max_size=1200):
    """
    Resizes an image proportionally so that the larger dimension equals max_size.
    :param image: PIL Image object to resize.
    :param max_size: Maximum size for the larger dimension.
    :return: Resized PIL Image object.
    """
    width, height = image.size
    
    if width <= max_size and height <= max_size:
        return image
    
    if width > height:
        scale_factor = max_size / width
    else:
        scale_factor = max_size / height
    
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)
    
    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    return resized_image

def center_image_on_white(background_size=(1200, 1200), input_image=None, output_image_path="output_image.jpg",check_result=False):
    """
    Places an input image at the center of a white background.
    If the input image is larger than the background, it resizes it proportionally
    while maintaining aspect ratio.
    :param background_size: Tuple specifying the size of the white background (width, height).
    :param input_image_path: Path to the input image.
    :param output_image_path: Path to save the output image.
    :return: The resulting PIL Image object.
    """
    if check_result==True:
        print("Check Result is True, skipping dimension fix")
        return input_image
    
    if input_image is None:
        raise ValueError("Input image cannot be None.")
    
    background = create_white_image(size=background_size)
    

    max_dimension = min(background_size)  # Use the smaller dimension of background
    
    processed_image = resize_image_proportionally(input_image, max_dimension)
    
    bg_width, bg_height = background.size
    img_width, img_height = processed_image.size
    x_offset = (bg_width - img_width) // 2
    y_offset = (bg_height - img_height) // 2
    
    if processed_image.mode in ('RGBA', 'LA') or (processed_image.mode == 'P' and 'transparency' in processed_image.info):
        white_bg = Image.new('RGB', processed_image.size, (255, 255, 255))
        if processed_image.mode == 'P':
            processed_image = processed_image.convert('RGBA')
        white_bg.paste(processed_image, mask=processed_image.split()[-1] if processed_image.mode == 'RGBA' else None)
        processed_image = white_bg
    
    background.paste(processed_image, (x_offset, y_offset))
    
    # background.save(output_image_path, quality=95)
    # print(f"Image saved at {output_image_path}")
    # print(f"Original size: {input_image.size}")
    # print(f"Final size on background: {background.size}")
    
    return background

