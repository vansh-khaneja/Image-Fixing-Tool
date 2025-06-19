from rembg import new_session, remove
from PIL import Image
import io

from PIL import Image, ImageDraw
import io, os
from rembg import remove, new_session

def remove_background_from_boxes(
    input_image, box_coordinates, output_path=None,
    model_name="u2net", padding=20,
    save_masks=False, mask_output_dir="debug_masks", check_result = False
):
    """
    Remove background from specific regions defined by bounding boxes,
    placing results on a white canvas of the same size as the original image.
    """
    if(check_result==True):
        print("Check Result is True, skipping background removal")
        return input_image
    # Create rembg session
    session = new_session(model_name)

    # Load image
    if isinstance(input_image, str):
        img = Image.open(input_image).convert("RGB")
    else:
        img = input_image.convert("RGB")
    width, height = img.size

    # Prepare white canvas instead of copying original
    result_img = Image.new("RGB", (width, height), (255, 255, 255))

    # Optional: prepare debug mask
    if save_masks:
        os.makedirs(mask_output_dir, exist_ok=True)
        combined_mask = Image.new("L", (width, height), 0)
        print(f"Debug masks will be saved to: {mask_output_dir}")

    # Process each box
    for i, (left, top, right, bottom) in enumerate(box_coordinates):
        print(f"Processing box {i+1}/{len(box_coordinates)}: {(left, top, right, bottom)}")
        # Compute padded box
        padded_left = max(0, left - padding)
        padded_top = max(0, top - padding)
        padded_right = min(width, right + padding)
        padded_bottom = min(height, bottom + padding)
        if padded_left >= padded_right or padded_top >= padded_bottom:
            print(f"Skipping invalid box {i+1}")
            continue

        # Crop and remove background
        patch = img.crop((padded_left, padded_top, padded_right, padded_bottom))
        with io.BytesIO() as buf:
            patch.save(buf, format="PNG")
            data = buf.getvalue()
        out = remove(data, session=session)
        proc = Image.open(io.BytesIO(out)).convert("RGBA")
        mask = proc.split()[3]

        # Save debug masks if requested
        if save_masks:
            patch.save(f"{mask_output_dir}/box_{i+1}_crop.png")
            mask.save(f"{mask_output_dir}/box_{i+1}_mask.png")
            proc.save(f"{mask_output_dir}/box_{i+1}_proc.png")
            # add to combined mask
            orig_w, orig_h = right-left, bottom-top
            dx, dy = left - padded_left, top - padded_top
            orig_mask = mask.crop((dx, dy, dx+orig_w, dy+orig_h))
            combined_mask.paste(orig_mask, (left, top))

        # Prepare white background for this box region
        white_bg = Image.new("RGBA", proc.size, (255, 255, 255, 255))
        white_bg.paste(patch, mask=mask)
        # Crop back to original box size
        orig_w, orig_h = right-left, bottom-top
        dx, dy = left - padded_left, top - padded_top
        final = white_bg.crop((dx, dy, dx+orig_w, dy+orig_h)).convert("RGB")

        # Paste onto white canvas
        result_img.paste(final, (left, top))

    # Save combined mask debugging overlays
    if save_masks:
        combined_mask.save(f"{mask_output_dir}/combined_mask.png")
        # visual overlay on white canvas
        overlay = Image.new("RGBA", (width, height), (255, 0, 0, 100))
        inv = Image.eval(combined_mask, lambda x: 255-x)
        bg = result_img.convert("RGBA")
        bg.paste(overlay, mask=inv)
        bg.save(f"{mask_output_dir}/mask_overlay.png")
        print("Debug masks saved")

    # Save or return
    if output_path:
        result_img.save(output_path, "JPEG", quality=95)
        print(f"Saved output to {output_path}")
        return result_img
    print("Processing complete")
    return result_img


def remove_background_from_boxes_advanced(input_image, box_coordinates, output_path=None, 
                                         model_name="isnet-general-use", background_color=(255, 255, 255)):

    try:
        # Create rembg session
        session = new_session(model_name)
        
        # Handle both PIL Image objects and file paths
        if isinstance(input_image, str):
            full_img = Image.open(input_image).convert("RGB")
        else:
            # Assume it's already a PIL Image
            full_img = input_image.convert("RGB")
            
        width, height = full_img.size
        
        # Create result image
        result_img = full_img.copy()
        
        # Process each box
        successful_boxes = 0
        
        for i, box in enumerate(box_coordinates):
            try:
                left, top, right, bottom = box
                
                # Validate and clamp coordinates
                left = max(0, min(left, width))
                top = max(0, min(top, height))
                right = max(left, min(right, width))
                bottom = max(top, min(bottom, height))
                
                # Skip invalid boxes
                if left >= right or top >= bottom:
                    print(f"Warning: Skipping invalid box {i+1}")
                    continue
                
                # Process the region
                cropped_region = full_img.crop((left, top, right, bottom))
                
                # Convert to bytes for rembg
                with io.BytesIO() as buf:
                    cropped_region.save(buf, format="PNG")
                    region_bytes = buf.getvalue()
                
                # Remove background
                output_data = remove(region_bytes, session=session)
                processed_region = Image.open(io.BytesIO(output_data)).convert("RGBA")
                
                # Create background with specified color
                bg_region = Image.new("RGB", cropped_region.size, background_color)
                
                # Extract mask and apply
                mask = processed_region.split()[3]
                bg_region.paste(cropped_region, mask=mask)
                
                # Paste back to result
                result_img.paste(bg_region, (left, top))
                successful_boxes += 1
                
            except Exception as e:
                print(f"Error processing box {i+1}: {str(e)}")
                continue
        
        print(f"Successfully processed {successful_boxes}/{len(box_coordinates)} boxes")
        
        # Save if output path provided
        if output_path:
            result_img.save(output_path, "JPEG", quality=95)
            print(f"Result saved to: {output_path}")
        
        return result_img
        
    except Exception as e:
        print(f"Error in background removal: {str(e)}")
        raise

def test_different_models(input_image, box_coordinates, output_dir="model_tests"):
    """
    Test different rembg models on the same image to compare results
    
    Args:
        input_image: PIL Image or path to image
        box_coordinates: List of bounding boxes
        output_dir: Directory to save test results
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    models_to_test = [
        "u2net",                # General purpose, less aggressive
        "u2net_human_seg",      # For human subjects
        "isnet-general-use",    # Your current model
        "silueta",              # Alternative general model
        "sam"                   # Segment Anything Model
    ]
    
    print("Testing different models...")
    
    for model in models_to_test:
        try:
            print(f"Testing model: {model}")
            result = remove_background_from_boxes(
                input_image=input_image,
                box_coordinates=box_coordinates,
                model_name=model,
                padding=30  # Extra padding for better results
            )
            
            output_path = os.path.join(output_dir, f"result_{model}.jpg")
            result.save(output_path)
            print(f"{model} result saved to: {output_path}")
            
        except Exception as e:
            print(f"Failed to test {model}: {str(e)}")
    
    print(f"\nAll test results saved in: {output_dir}")
    print("Compare the results to choose the best model for your use case!")
