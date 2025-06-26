from ultralytics import YOLO
import cv2
import numpy as np
from checks.check_center import get_box_center



model = YOLO('yolo_self_train_new.pt') 


def draw_simple_bbox(img, box, class_name, confidence):
    """Draw simple thin bounding box with small text"""
    x1, y1, x2, y2 = map(int, box)

    # Simple thin rectangle
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 1)

    # Small text label
    label = f"{class_name} {confidence:.2f}"
    cv2.putText(img, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    return img


def calculate_intersection_area(box1, box2):
    """Calculate intersection area between two boxes"""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    # Calculate intersection coordinates
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)

    # No intersection
    if x2_i <= x1_i or y2_i <= y1_i:
        return 0.0

    return (x2_i - x1_i) * (y2_i - y1_i)


def calculate_union_area(box1, box2):
    """Calculate union area of two boxes"""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    # Calculate union coordinates (bounding box that encompasses both)
    x1_u = min(x1_1, x1_2)
    y1_u = min(y1_1, y1_2)
    x2_u = max(x2_1, x2_2)
    y2_u = max(y2_1, y2_2)

    return (x2_u - x1_u) * (y2_u - y1_u)


def calculate_individual_areas(box1, box2):
    """Calculate individual areas of two boxes"""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)

    return area1, area2


def is_box_contained(box1, box2):
    """Check if box1 is completely contained within box2"""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    # box1 is contained in box2 if all corners of box1 are inside box2
    return (x1_1 >= x1_2 and y1_1 >= y1_2 and x2_1 <= x2_2 and y2_1 <= y2_2)


def calculate_proximity_distance(box1, box2):
    """
    Calculate the minimum distance between two boxes.
    Returns 0 if boxes overlap, otherwise returns minimum gap distance.
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Check if boxes overlap
    if not (x2_1 <= x1_2 or x2_2 <= x1_1 or y2_1 <= y1_2 or y2_2 <= y1_1):
        return 0  # Boxes overlap
    
    # Calculate distances in each direction
    # Horizontal distance
    if x2_1 <= x1_2:  # box1 is to the left of box2
        horizontal_dist = x1_2 - x2_1
    elif x2_2 <= x1_1:  # box2 is to the left of box1
        horizontal_dist = x1_1 - x2_2
    else:
        horizontal_dist = 0  # Boxes overlap horizontally
    
    # Vertical distance
    if y2_1 <= y1_2:  # box1 is above box2
        vertical_dist = y1_2 - y2_1
    elif y2_2 <= y1_1:  # box2 is above box1
        vertical_dist = y1_1 - y2_2
    else:
        vertical_dist = 0  # Boxes overlap vertically
    
    # If boxes are side by side (only horizontal gap)
    if vertical_dist == 0:
        return horizontal_dist
    
    # If boxes are stacked (only vertical gap)
    if horizontal_dist == 0:
        return vertical_dist
    
    # If boxes are diagonal (both horizontal and vertical gap)
    # Return the euclidean distance between closest corners
    return np.sqrt(horizontal_dist**2 + vertical_dist**2)


def are_boxes_close(box1, box2, proximity_threshold=20):
    """
    Check if two boxes are close enough to be considered for merging.
    Returns False immediately if proximity_threshold is 0.
    """
    # If proximity_threshold is 0, don't consider any boxes as "close"
    if proximity_threshold <= 0:
        return False
    
    distance = calculate_proximity_distance(box1, box2)
    
    # Simple comparison - no adaptive threshold for now
    is_close = distance <= proximity_threshold
    
    # Debug print (remove this later)
    if distance > 0:  # Only print for non-overlapping boxes
        print(f"Box distance: {distance:.1f}, threshold: {proximity_threshold}, close: {is_close}")
    
    return is_close


def should_merge_boxes(box1, box2, union_efficiency_threshold=0.7, proximity_threshold=20):
    """
    Enhanced merging logic with containment check and proximity merging

    Merge if:
    1. One box is completely contained in another, OR
    2. Boxes are very close to each other (proximity merging), OR
    3. Boxes have significant intersection AND high union efficiency
    """
    # Check containment first - if one box is inside another, always merge
    if is_box_contained(box1, box2) or is_box_contained(box2, box1):
        return True
    
    # Check proximity - if boxes are very close, merge them
    if proximity_threshold > 0 and are_boxes_close(box1, box2, proximity_threshold):
        return True

    # Check intersection
    intersection_area = calculate_intersection_area(box1, box2)

    # If no intersection, don't merge
    if intersection_area == 0:
        return False

    # Calculate areas
    area1, area2 = calculate_individual_areas(box1, box2)
    smaller_area = min(area1, area2)
    
    # Require significant intersection (at least 20% of the smaller box)
    intersection_ratio = intersection_area / smaller_area if smaller_area > 0 else 0
    if intersection_ratio < 0.2:  # Less than 20% intersection
        return False

    # Only check union efficiency if boxes have significant intersection
    union_area = calculate_union_area(box1, box2)
    combined_area = area1 + area2
    efficiency = combined_area / union_area if union_area > 0 else 0

    return efficiency >= union_efficiency_threshold


def merge_boxes_smart(boxes, confidences, class_names, union_efficiency_threshold=0.7, proximity_threshold=20):
    """
    Smart merging based on union area efficiency and proximity
    """
    if len(boxes) == 0:
        return [], [], [], 0

    n = len(boxes)
    merged_boxes = []
    merged_confidences = []
    merged_class_names = []
    used = [False] * n
    merges_count = 0

    for i in range(n):
        if used[i]:
            continue

        # Start with current box
        current_group = [i]
        used[i] = True

        # Find all boxes that should merge with this group
        changed = True
        while changed:
            changed = False
            for j in range(n):
                if used[j]:
                    continue

                # Check if box j should merge with any box in current group
                should_add = False
                for group_idx in current_group:
                    if should_merge_boxes(boxes[group_idx], boxes[j], union_efficiency_threshold, proximity_threshold):
                        should_add = True
                        break

                if should_add:
                    current_group.append(j)
                    used[j] = True
                    changed = True

        # Create final box for this group
        if len(current_group) == 1:
            # Single box
            idx = current_group[0]
            merged_boxes.append(boxes[idx])
            merged_confidences.append(confidences[idx])
            merged_class_names.append(class_names[idx])
        else:
            # Merge multiple boxes
            merges_count += 1
            group_boxes = [boxes[i] for i in current_group]
            group_confs = [confidences[i] for i in current_group]
            group_classes = [class_names[i] for i in current_group]

            # Calculate merged bounding box (union)
            x1_min = min([box[0] for box in group_boxes])
            y1_min = min([box[1] for box in group_boxes])
            x2_max = max([box[2] for box in group_boxes])
            y2_max = max([box[3] for box in group_boxes])

            merged_box = [x1_min, y1_min, x2_max, y2_max]

            # Use highest confidence
            best_idx = np.argmax(group_confs)
            merged_conf = group_confs[best_idx]

            # Use most common class or highest confidence class
            unique_classes = list(set(group_classes))
            if len(unique_classes) == 1:
                merged_class = unique_classes[0]
            else:
                merged_class = group_classes[best_idx]  # Use class of highest confidence detection

            merged_boxes.append(merged_box)
            merged_confidences.append(merged_conf)
            merged_class_names.append(merged_class)

    return merged_boxes, merged_confidences, merged_class_names, merges_count


def remove_contained_boxes(boxes, confidences, class_names):
    """
    Remove boxes that are completely contained within other boxes
    Keep the box with higher confidence when one is contained in another
    """
    if len(boxes) <= 1:
        return boxes, confidences, class_names, 0

    n = len(boxes)
    to_remove = set()
    removed_count = 0

    for i in range(n):
        if i in to_remove:
            continue

        for j in range(n):
            if i == j or j in to_remove:
                continue

            # Check if box i is contained in box j
            if is_box_contained(boxes[i], boxes[j]):
                # Keep the box with higher confidence
                if confidences[i] <= confidences[j]:
                    to_remove.add(i)
                    removed_count += 1
                else:
                    to_remove.add(j)
                    removed_count += 1
            # Check if box j is contained in box i
            elif is_box_contained(boxes[j], boxes[i]):
                # Keep the box with higher confidence
                if confidences[j] <= confidences[i]:
                    to_remove.add(j)
                    removed_count += 1
                else:
                    to_remove.add(i)
                    removed_count += 1

    # Filter out contained boxes
    filtered_boxes = [boxes[i] for i in range(n) if i not in to_remove]
    filtered_confidences = [confidences[i] for i in range(n) if i not in to_remove]
    filtered_class_names = [class_names[i] for i in range(n) if i not in to_remove]

    return filtered_boxes, filtered_confidences, filtered_class_names, removed_count


def merge_boxes_smart_with_containment_removal(boxes, confidences, class_names, union_efficiency_threshold=0.7, proximity_threshold=20):
    """
    Enhanced smart merging with containment removal and proximity merging:
    1. First merge overlapping/touching/close boxes
    2. Then remove any boxes completely contained within others
    """
    if len(boxes) == 0:
        return [], [], [], 0, 0

    # Step 1: Smart merging with proximity (your existing logic + proximity)
    merged_boxes, merged_confidences, merged_class_names, merges_count = merge_boxes_smart(
        boxes, confidences, class_names, union_efficiency_threshold, proximity_threshold
    )

    # Step 2: Remove contained boxes
    final_boxes, final_confidences, final_class_names, removed_count = remove_contained_boxes(
        merged_boxes, merged_confidences, merged_class_names
    )

    return final_boxes, final_confidences, final_class_names, merges_count, removed_count


from PIL import Image
import numpy as np

def process_image_with_enhanced_merging(image,
                                      confidence_threshold=0.3,
                                      union_efficiency_threshold=0.1,
                                      proximity_threshold=20,
                                      use_smart_merge=True):


    # Convert PIL Image to BGR numpy array if necessary
    if isinstance(image, Image.Image):
        img_np = np.array(image)  # Convert PIL Image to RGB numpy array
        input_for_model = img_np[:, :, ::-1].copy()  # Convert RGB to BGR
    elif isinstance(image, str):
        input_for_model = image  # Use path directly
    else:
        raise TypeError("image must be a path (str) or PIL Image")

    # Run YOLO detection
    results = model(input_for_model, conf=confidence_threshold)

    # Initialize variables
    final_boxes = []
    final_confidences = []
    final_class_names = []
    img_output = None  # Will store the output image with boxes

    # Process results
    for r in results:
        # Get the image in BGR format (consistent for both path and PIL input)
        img_output = r.orig_img.copy()

        if r.boxes is not None:
            boxes = r.boxes.xyxy.cpu().numpy()
            confidences = r.boxes.conf.cpu().numpy()
            class_ids = r.boxes.cls.cpu().numpy().astype(int)
            class_names = [r.names[int(cls)] for cls in class_ids]

            # Filter by confidence
            valid_indices = confidences >= confidence_threshold
            boxes = boxes[valid_indices]
            confidences = confidences[valid_indices]
            class_names = [class_names[i] for i in range(len(class_names)) if valid_indices[i]]
            original_count = len(boxes)

            if use_smart_merge and len(boxes) > 1:
                # Enhanced merging with proximity
                final_boxes, final_confidences, final_class_names, merges_count, removed_count = merge_boxes_smart_with_containment_removal(
                    boxes, confidences, class_names, union_efficiency_threshold, proximity_threshold
                )
                info = {
                    'original_detections': original_count,
                    'after_merging': len(final_boxes) + removed_count,
                    'final_boxes': len(final_boxes),
                    'merges_performed': merges_count,
                    'contained_boxes_removed': removed_count,
                    'efficiency_threshold': union_efficiency_threshold,
                    'proximity_threshold': proximity_threshold,
                    'confidence_threshold': confidence_threshold
                }
                # Draw boxes
                for box, conf, cls_name in zip(final_boxes, final_confidences, final_class_names):
                    img_output = draw_simple_bbox(img_output, box, cls_name, conf)
            else:
                final_boxes = boxes.tolist()
                final_confidences = confidences.tolist()
                final_class_names = class_names
                info = {
                    'original_detections': original_count,
                    'after_merging': original_count,
                    'final_boxes': original_count,
                    'merges_performed': 0,
                    'contained_boxes_removed': 0,
                    'efficiency_threshold': 'disabled',
                    'proximity_threshold': 'disabled',
                    'confidence_threshold': confidence_threshold
                }
                # Draw boxes
                for box, conf, cls_name in zip(final_boxes, final_confidences, final_class_names):
                    img_output = draw_simple_bbox(img_output, box, cls_name, conf)
        else:
            info = {
                'original_detections': 0,
                'after_merging': 0,
                'final_boxes': 0,
                'merges_performed': 0,
                'contained_boxes_removed': 0,
                'efficiency_threshold': 'no_detections',
                'proximity_threshold': 'no_detections',
                'confidence_threshold': confidence_threshold
            }

    # Format bounding boxes
    bounding_boxes = []
    box_coords=[]
    centroids=[]
    for i, (box, conf, cls_name) in enumerate(zip(final_boxes, final_confidences, final_class_names)):
        bbox_info = {
            'box_id': i + 1,
            'class_name': cls_name,
            'confidence': float(conf),
            'coordinates': {
                'x1': float(box[0]),
                'y1': float(box[1]),
                'x2': float(box[2]),
                'y2': float(box[3])
            },
            'width': float(box[2] - box[0]),
            'height': float(box[3] - box[1]),
            'area': float((box[2] - box[0]) * (box[3] - box[1]))
        }
        bounding_boxes.append(bbox_info)
        if len(bounding_boxes) < 1:
            print("No object detected")
        box_coords = []
        centroids = []
        for box in bounding_boxes:
            x1, y1, x2, y2 = box['coordinates'].values()
            box_coords.append((int(x1), int(y1), int(x2), int(y2)))
            x,y = get_box_center(x1, y1, x2, y2) 
            centroids.append((int(x), int(y)))

    return img_output, bounding_boxes, info, box_coords, centroids