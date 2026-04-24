import os
import cv2
import numpy as np
import base64
import math
from django.shortcuts import render
from django.conf import settings

# --- PRODUCT COORDINATE DATABASE ---
PRODUCT_CONFIGS = {
    'shirt.jpg': { 'dst_pts': np.float32([[280, 250], [480, 270], [460, 450], [270, 430]]) },
    'hoodie.jpg': { 'dst_pts': np.float32([[250, 300], [450, 300], [450, 500], [250, 500]]) },
    'mug.jpg': { 'dst_pts': np.float32([[150, 200], [350, 220], [350, 400], [150, 380]]) }
}

def upload_view(request):
    context = {}
    
    if request.method == 'POST':
        # 1. HANDLE DESIGN PERSISTENCE
        design_file = request.FILES.get('design_image')
        # Check if we have a previous design stored in session to allow slider updates
        if design_file:
            # Save new upload to session as base64 string
            file_bytes = design_file.read()
            request.session['saved_design'] = base64.b64encode(file_bytes).decode('utf-8')
            design_data = file_bytes
        elif 'saved_design' in request.session:
            # Use the design from the previous upload
            design_data = base64.b64decode(request.session['saved_design'])
        else:
            return render(request, 'upload.html', {'error_message': 'Please upload a design first!'})

        try:
            # 2. CONVERT TO OPENCV IMAGE
            nparr = np.frombuffer(design_data, np.uint8)
            design_img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
            
            if design_img is None:
                raise Exception("Invalid image file.")

            # 3. PATH SEARCH FOR BASE PRODUCT
            selected_base = request.POST.get('base_product', 'shirt.jpg')
            search_paths = [
                os.path.join(settings.BASE_DIR, 'static', selected_base),
                os.path.join(settings.BASE_DIR, 'customizer', 'static', selected_base),
                os.path.join(settings.BASE_DIR, 'staticfiles', selected_base),
                selected_base
            ]
            
            base_img = None
            for path in search_paths:
                if os.path.exists(path):
                    base_img = cv2.imread(path)
                    if base_img is not None: break

            if base_img is None:
                raise Exception(f"Base product {selected_base} not found.")

            # 4. PREPARE DESIGN
            if len(design_img.shape) == 2 or design_img.shape[2] == 3:
                design_img = cv2.cvtColor(design_img, cv2.COLOR_BGR2BGRA)

            config = PRODUCT_CONFIGS.get(selected_base, PRODUCT_CONFIGS['shirt.jpg'])
            h, w = design_img.shape[:2]
            src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
            dst_pts = np.copy(config['dst_pts'])
            
            # 5. GET SLIDER VALUES
            stage = request.POST.get('processing_stage', 'blending')
            intensity = int(request.POST.get('blend_intensity', 50)) / 100.0
            scale = int(request.POST.get('scale_percent', 100)) / 100.0
            offset_x = int(request.POST.get('offset_x', 0))
            offset_y = int(request.POST.get('offset_y', 0))
            rotation = int(request.POST.get('rotation', 0))

            # 6. TRANSFORMATION MATH
            cx, cy = np.mean(dst_pts[:, 0]), np.mean(dst_pts[:, 1])
            angle_rad = math.radians(rotation)

            for pt in dst_pts:
                px, py = cx + (pt[0] - cx) * scale, cy + (pt[1] - cy) * scale
                tx, ty = px - cx, py - cy
                rx = tx * math.cos(angle_rad) - ty * math.sin(angle_rad)
                ry = tx * math.sin(angle_rad) + ty * math.cos(angle_rad)
                pt[0], pt[1] = rx + cx + offset_x, ry + cy + offset_y

            # 7. WARPING AND BLENDING
            matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
            bh, bw = base_img.shape[:2]
            warped = cv2.warpPerspective(design_img, matrix, (bw, bh))
            alpha = warped[:, :, 3] / 255.0
            
            if stage == 'blending':
                base_gray = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
                shadow_map = (base_gray / 255.0) * intensity + (1.0 - intensity)
            else:
                shadow_map = 1.0
            
            for c in range(3):
                base_img[:, :, c] = (alpha * (warped[:, :, c] * shadow_map) + (1 - alpha) * base_img[:, :, c])
            
            # 8. OUTPUT
            _, buffer = cv2.imencode('.jpg', base_img)
            context['image_url'] = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
            context.update({
                'selected_base': selected_base, 'processing_stage': stage,
                'blend_intensity': int(intensity * 100), 'current_scale': int(scale * 100),
                'current_x': offset_x, 'current_y': offset_y, 'current_rotation': rotation
            })
            
            return render(request, 'upload.html', context)

        except Exception as e:
            context['error_message'] = str(e)
            return render(request, 'upload.html', context)

    return render(request, 'upload.html')

def landing_view(request):
    return render(request, 'landing.html')