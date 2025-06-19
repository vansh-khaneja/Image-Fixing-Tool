from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io
import tempfile
from PIL import Image

# Import your existing modules
from utils.coordinates import process_image_with_enhanced_merging
from checks.check_background import check_background
from agents.fix_dimensions import center_image_on_white
from agents.fix_background import remove_background_from_boxes
from agents.fix_center import rearrange_image_content

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process-image/")
async def process_image(file: UploadFile = File(...)):
    # Read uploaded file
    contents = await file.read()
    input_image = Image.open(io.BytesIO(contents))
    
    # Convert to RGB if needed (handles RGBA, P, L, etc.)
    if input_image.mode != 'RGB':
        input_image = input_image.convert('RGB')
    
    # Create temp file for background check
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        input_image.save(temp_file.name, 'JPEG')
        temp_path = temp_file.name
    
    # Your existing pipeline
    check_background_result = check_background(temp_path)
    
    # Fix dimensions
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        dimension_temp_path = temp_file.name
    
    image_dimension_fixed = center_image_on_white(
        input_image=input_image,
        output_image_path=dimension_temp_path,
        check_result=False
    )
    
    # Get bounding boxes
    processed_img, bounding_boxes, stats, box_coords, centroids = process_image_with_enhanced_merging(image_dimension_fixed,proximity_threshold=4)
    
    # Remove background
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        bg_temp_path = temp_file.name
    
    with tempfile.TemporaryDirectory() as mask_temp_dir:
        image_background_fixed = remove_background_from_boxes(
            input_image=image_dimension_fixed,
            box_coordinates=box_coords,
            model_name="u2net",
            padding=60,
            save_masks=True,
            mask_output_dir=mask_temp_dir,
            output_path=bg_temp_path,
            check_result=check_background_result
        )
    
    # Rearrange content
    processed_img_final, bounding_boxes_final, stats_final, box_coords_final, centroids_final = process_image_with_enhanced_merging(image_background_fixed,proximity_threshold=4)
    
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        final_temp_path = temp_file.name
    
    rearranged_img = rearrange_image_content(
        image_background_fixed,
        box_coords_final,
        spacing_mode="balanced",
        save_path=final_temp_path,
        check_result=False
    )
    
    # Return the processed image
    img_byte_arr = io.BytesIO()
    rearranged_img.save(img_byte_arr, format='JPEG', quality=95)
    img_byte_arr.seek(0)
    
    print(f"Response image size: {len(img_byte_arr.getvalue())} bytes")
    
    return StreamingResponse(
        io.BytesIO(img_byte_arr.read()), 
        media_type="image/jpeg",
        headers={
            "Content-Disposition": "inline; filename=processed_image.jpg",
            "Cache-Control": "no-cache"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)