from fastapi import FastAPI, File, UploadFile, Form
from typing import Optional
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io
import tempfile
from PIL import Image
import os
# Import your existing modules
from utils.coordinates import process_image_with_enhanced_merging
from checks.check_background import check_background
from checks.check_center import check_products_alignment
from checks.check_dimension import check_image_dimensions
from agents.fix_dimensions import center_image_on_white
from agents.fix_background import remove_background_from_boxes,fix_transparency_if_needed
from agents.fix_center import rearrange_image_content
from agents.fix_noise import remove_noise_simple

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthcheck/")
async def healthcheck():
    return {"status": "ok", "message": "API is running successfully"}

@app.post("/check_image/")
async def check_image(
    file: UploadFile = File(...),
    target_width: Optional[int] = Form(1200),
    target_height: Optional[int] = Form(1200)
):
    contents = await file.read()
    input_image = Image.open(io.BytesIO(contents))
    if input_image.mode != 'RGB':
        input_image = input_image.convert('RGB')
    
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        input_image.save(temp_file.name, 'JPEG')
        temp_path = temp_file.name
    
    try:
        check_background_result = check_background(temp_path)
        print(f"Background check result: {check_background_result}")
        
        check_image_dimensions_result = check_image_dimensions(
            input_image, 
            target_width=target_width, 
            target_height=target_height
        )
        print(f"Dimension check result: {check_image_dimensions_result}")
        
        processed_img, bounding_boxes, stats, box_coords, centroids = process_image_with_enhanced_merging(
            input_image, proximity_threshold=4
        )
        
        check_products_alignment_result = check_products_alignment(
            input_image, centroids, alignment_threshold=50, spacing_mode="balanced"
        )
        print(f"Products alignment check result: {check_products_alignment_result}")
        
        # Return only the check results as boolean values
        return {
            "background_check": bool(check_background_result),
            "dimension_check": bool(check_image_dimensions_result),
            "alignment_check": bool(check_products_alignment_result),
            "target_dimensions": {
                "width": target_width,
                "height": target_height
            }
        }
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except:
            pass

@app.post("/process-image/")
async def process_image(
    file: UploadFile = File(...),
    fix_dimensions: Optional[str] = Form("true"),
    fix_background: Optional[str] = Form("true"), 
    fix_alignment: Optional[str] = Form("true"),
    target_width: Optional[int] = Form(1200),
    target_height: Optional[int] = Form(1200)
):
    # Convert string form data to booleans
    should_fix_dimensions = fix_dimensions.lower() == "true"
    should_fix_background = fix_background.lower() == "true"
    should_fix_alignment = fix_alignment.lower() == "true"
    
    print(f"Processing options - Dimensions: {should_fix_dimensions}, Background: {should_fix_background}, Alignment: {should_fix_alignment}")
    print(f"Target dimensions: {target_width}x{target_height}")
    
    # Read uploaded file
    contents = await file.read()
    input_image = Image.open(io.BytesIO(contents))

    input_image,had_transparency = fix_transparency_if_needed(input_image)
    # Convert to RGB if needed
    if input_image.mode != 'RGB':
        input_image = input_image.convert('RGB')
       

    # Create temp file for background check
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        input_image.save(temp_file.name, 'JPEG')
        temp_path = temp_file.name
    
    try:
        # Run initial checks with configurable dimensions
        check_background_result = check_background(temp_path)
        print(f"Background check result: {check_background_result}")
        
        check_image_dimensions_result = check_image_dimensions(
            input_image, 
            target_width=target_width, 
            target_height=target_height
        )
        print(f"Dimension check result: {check_image_dimensions_result}")
        
        processed_img, bounding_boxes, stats, box_coords, centroids = process_image_with_enhanced_merging(input_image, proximity_threshold=4)
        
        check_products_alignment_result = check_products_alignment(input_image, centroids, alignment_threshold=50, spacing_mode="balanced")
        print(f"Products alignment check result: {check_products_alignment_result}")
        
        # Start with original image
        current_image = input_image
        
        # STEP 1: Fix dimensions (if requested)
        if should_fix_dimensions:
            print("🔧 Fixing dimensions...")
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                dimension_temp_path = temp_file.name
            
            current_image = center_image_on_white(
                background_size=(target_width, target_height),  # Use configurable dimensions
                input_image=current_image,
                output_image_path=dimension_temp_path,
                check_result=check_image_dimensions_result
            )
            
            current_image.save('dimension_fixed.jpg')
            try:
                os.unlink(dimension_temp_path)
            except:
                pass
        else:
            print("⏭️  Skipping dimension fix")
        
        # STEP 2: Fix background (if requested)
        if should_fix_background:
            print("🔧 Fixing background...")
            # Get fresh bounding boxes from current image
            processed_img, bounding_boxes, stats, box_coords, centroids = process_image_with_enhanced_merging(current_image, proximity_threshold=4)
            
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                bg_temp_path = temp_file.name
            
            with tempfile.TemporaryDirectory() as mask_temp_dir:
                current_image = remove_background_from_boxes(
                    input_image=current_image,
                    box_coordinates=box_coords,
                    model_name="u2net",
                    padding=60,
                    save_masks=True,
                    mask_output_dir=mask_temp_dir,
                    output_path=bg_temp_path,
                    check_result=check_background_result
                )
                current_image.save('background_fixed.jpg')
            
            try:
                os.unlink(bg_temp_path)
            except:
                pass
        else:
            print("⏭️  Skipping background fix")
        
        # STEP 3: Fix alignment (if requested)
        if should_fix_alignment:
            print("🔧 Fixing alignment...")
            # Get fresh bounding boxes from current image
            processed_img_final, bounding_boxes_final, stats_final, box_coords_final, centroids_final = process_image_with_enhanced_merging(current_image, proximity_threshold=4)
            
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                final_temp_path = temp_file.name
            
            current_image = rearrange_image_content(
                current_image,
                box_coords_final,
                spacing_mode="balanced",
                save_path=final_temp_path,
                check_result=check_products_alignment_result
            )
            current_image.save('alignment_fixed.jpg')
            
            try:
                os.unlink(final_temp_path)
            except:
                pass
        else:
            print("⏭️  Skipping alignment fix")
        # processed_img, bounding_boxes, stats, box_coords, centroids = process_image_with_enhanced_merging(current_image, proximity_threshold=4)

        current_image = remove_noise_simple(current_image,had_transparency=had_transparency,debug_path='debug.jpg')
        
        # Return the processed image
        img_byte_arr = io.BytesIO()
        current_image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        
        print(f"✅ Processing complete! Response image size: {len(img_byte_arr.getvalue())} bytes")
        
        return StreamingResponse(
            io.BytesIO(img_byte_arr.read()),
            media_type="image/jpeg",
            headers={
                "Content-Disposition": "inline; filename=processed_image.jpg",
                "Cache-Control": "no-cache"
            }
        )
    
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)