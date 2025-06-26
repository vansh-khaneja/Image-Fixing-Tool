from PIL import Image
import numpy as np
import cv2

def remove_noise_simple(img,
                        had_transparency = True,
                        dark_thresh: int = 240,
                        area_thresh: int = 500,
                        white_threshold: int = 245,
                        fill_color: tuple = (255, 255, 255),
                        debug_path: str = None) -> 'Union[np.ndarray, Image.Image]':
    """
    Simplest dark-spot removal on light backgrounds, skipping small blobs inside larger unremoved regions.

    - Save debug image with parent contours and only removed blobs shown.
    """

    if had_transparency:
        return img
    pil_input = False
    if isinstance(img, Image.Image):
        pil_input = True
        img = img.convert('RGB')
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    elif isinstance(img, np.ndarray):
        cv_img = img.copy()
    else:
        raise TypeError(f"remove_noise_simple: unsupported type {type(img)}")

    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, dark_thresh, 255, cv2.THRESH_BINARY_INV)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)

    parent_mask = np.zeros_like(binary, dtype=np.uint8)
    for i in range(1, num_labels):
        _, _, _, _, area = stats[i]
        if area > area_thresh:
            parent_mask[labels == i] = 255

    parent_contours, _ = cv2.findContours(parent_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if debug_path:
        debug_img = np.full_like(cv_img, 255)  # white canvas
        cv2.drawContours(debug_img, parent_contours, -1, (0, 0, 255), 2)

    for i in range(1, num_labels):
        _, _, _, _, area = stats[i]
        if area > area_thresh:
            continue

        mask_blob = (labels == i).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask_blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue

        cx, cy = centroids[i]
        inside_parent = any(cv2.pointPolygonTest(parent, (cx, cy), False) >= 0 for parent in parent_contours)
        if inside_parent:
            continue

        # Directly erase the blob outside any parent contour
        cv_img[labels == i] = fill_color[::-1]  # remove from main
        if debug_path:
            debug_img[labels == i] = (0, 0, 0)  # draw in debug

    if debug_path:
        cv2.imwrite(debug_path, debug_img)

    if pil_input:
        return Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
    return cv_img
