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
        design_file = request.FILES.get('design_image')
        
        if not design_file:
            return render(request, 'upload.html', {'error_message': 'Please upload a design first!'})

        try:
            # 1. Memory-Safe Image Loading
            file_bytes = np.frombuffer(design_file.read(), np.uint8)
            design_img = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
            
            if design_img is None:
                raise Exception("Invalid image file uploaded.")

            # 2. Product Selection & Pathing
            selected_base = request.POST.get('base_product', 'shirt.jpg')
            base_path = os.path.join(settings.BASE_DIR, 'static', selected_base)
            base_img = cv2.imread(base_path)

            if base_img is None:
                # Fallback pathing for local vs production
                base_path = os.path.join(settings.BASE_DIR, 'customizer', 'static', selected_base)
                base_img = cv2.imread(base_path)
            
            if base_img is None:
                raise Exception(f"Product image {selected_base} not found.")

            # 3. Format Design Image
            if len(design_img.shape) == 2 or design_img.shape[2] == 3:
                design_img = cv2.cvtColor(design_img, cv2.COLOR_BGR2BGRA)

            config = PRODUCT_CONFIGS.get(selected_base, PRODUCT_CONFIGS['shirt.jpg'])
            h, w = design_img.shape[:2]
            src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
            dst_pts = np.copy(config['dst_pts'])
            
            # --- TRANSFORMATION LOGIC ---
            stage = request.POST.get('processing_stage', 'blending')
            intensity = int(request.POST.get('blend_intensity', 50)) / 100.0
            scale = int(request.POST.get('scale_percent', 100)) / 100.0
            offset_x = int(request.POST.get('offset_x', 0))
            offset_y = int(request.POST.get('offset_y', 0))
            rotation = int(request.POST.get('rotation', 0))

            cx, cy = np.mean(dst_pts[:, 0]), np.mean(dst_pts[:, 1])
            angle_rad = math.radians(rotation)

            for pt in dst_pts:
                px, py = cx + (pt[0] - cx) * scale, cy + (pt[1] - cy) * scale
                tx, ty = px - cx, py - cy
                rx = tx * math.cos(angle_rad) - ty * math.sin(angle_rad)
                ry = tx * math.sin(angle_rad) + ty * math.cos(angle_rad)
                pt[0], pt[1] = rx + cx + offset_x, ry + cy + offset_y

            # 4. Warping & Blending
            matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
            shirt_h, shirt_w = base_img.shape[:2]
            warped_design = cv2.warpPerspective(design_img, matrix, (shirt_w, shirt_h))
            alpha_channel = warped_design[:, :, 3] / 255.0
            
            if stage == 'blending':
                base_gray = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
                shadow_map = (base_gray / 255.0) * intensity + (1.0 - intensity)
            else:
                shadow_map = 1.0
            
            for c in range(0, 3):
                base_img[:, :, c] = (alpha_channel * (warped_design[:, :, c] * shadow_map) + (1 - alpha_channel) * base_img[:, :, c])
            
            # 5. Output for Template
            _, buffer = cv2.imencode('.jpg', base_img)
            context['image_url'] = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
            
            context.update({
                'selected_base': selected_base, 'processing_stage': stage,
                'blend_intensity': int(intensity * 100), 'current_scale': int(scale * 100),
                'current_x': offset_x, 'current_y': offset_y, 'current_rotation': rotation
            })
            
            return render(request, 'upload.html', context)

        except Exception as e:
            context['error_message'] = f"Studio Error: {str(e)}"
            return render(request, 'upload.html', context)

    return render(request, 'upload.html')

def landing_view(request):
    return render(request, 'landing.html')