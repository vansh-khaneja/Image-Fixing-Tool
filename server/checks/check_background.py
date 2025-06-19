from rembg import remove
from PIL import Image
import numpy as np
import io


def check_background(image_path, white_thresh=240, ratio_thresh=0.85):

    try:
        with open(image_path, 'rb') as f:
            input_bytes = f.read()
        
        mask_bytes = remove(input_bytes, only_mask=True)
        mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L")
        mask_np = np.array(mask_img)
        
        orig_img = Image.open(image_path).convert("RGB")
        rgb_np = np.array(orig_img)
        
        bg_mask = mask_np < 10
        if not np.any(bg_mask):
            return False
        
        bg_pixels = rgb_np[bg_mask]
        
        # Use all RGB channels for better white detection
        # A pixel is white if all RGB values are above threshold
        white_pixels = np.sum(np.all(bg_pixels >= white_thresh, axis=1))
        white_ratio = white_pixels / len(bg_pixels)
        
        return white_ratio >= ratio_thresh
        
    except:
        return False


