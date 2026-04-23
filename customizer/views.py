from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os
import cv2
import numpy as np
import base64
import math

# --- PRODUCT COORDINATE DATABASE ---
PRODUCT_CONFIGS = {
    'shirt.jpg': { 'dst_pts': np.float32([[280, 250], [480, 270], [460, 450], [270, 430]]) },
    'hoodie.jpg': { 'dst_pts': np.float32([[250, 300], [450, 300], [450, 500], [250, 500]]) },
    'mug.jpg': { 'dst_pts': np.float32([[150, 200], [350, 220], [350, 400], [150, 380]]) }
}

def upload_view(request):
    context = {}
    if request.method == 'POST':
        previous_design = request.POST.get('previous_design', '')
        design_filename = previous_design
        
        if request.FILES.get('design_image'):
            uploaded_file = request.FILES['design_image']
            fs = FileSystemStorage()
            design_filename = fs.save(uploaded_file.name, uploaded_file)
            
        if not design_filename:
            return render(request, 'upload.html', {'error_message': 'Please upload a design first!'})
            
        context['previous_design'] = design_filename
        
        # --- CATCH ALL SETTINGS ---
        selected_base = request.POST.get('base_product', 'shirt.jpg')
        stage = request.POST.get('processing_stage', 'blending')
        intensity = int(request.POST.get('blend_intensity', 50)) / 100.0
        scale = int(request.POST.get('scale_percent', 100)) / 100.0
        offset_x = int(request.POST.get('offset_x', 0))
        offset_y = int(request.POST.get('offset_y', 0))
        rotation = int(request.POST.get('rotation', 0))
        
        context.update({
            'selected_base': selected_base, 'processing_stage': stage,
            'blend_intensity': int(request.POST.get('blend_intensity', 50)),
            'current_scale': int(scale * 100), 'current_x': offset_x,
            'current_y': offset_y, 'current_rotation': rotation
        })
        
        design_path = os.path.join(settings.MEDIA_ROOT, design_filename)
        base_path = os.path.join(settings.MEDIA_ROOT, selected_base)
        config = PRODUCT_CONFIGS.get(selected_base, PRODUCT_CONFIGS['shirt.jpg'])
        
        try:
            base_img = cv2.imread(base_path)
            design_img = cv2.imread(design_path, cv2.IMREAD_UNCHANGED) 
            if len(design_img.shape) == 2 or design_img.shape[2] == 3:
                design_img = cv2.cvtColor(design_img, cv2.COLOR_BGR2BGRA)

            h, w = design_img.shape[:2]
            src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
            dst_pts = np.copy(config['dst_pts'])
            
            # --- TRANSFORMATION MATH ---
            cx, cy = np.mean(dst_pts[:, 0]), np.mean(dst_pts[:, 1])
            angle_rad = math.radians(rotation)

            for pt in dst_pts:
                # 1. Scale
                px, py = cx + (pt[0] - cx) * scale, cy + (pt[1] - cy) * scale
                # 2. Rotate
                tx, ty = px - cx, py - cy
                rx = tx * math.cos(angle_rad) - ty * math.sin(angle_rad)
                ry = tx * math.sin(angle_rad) + ty * math.cos(angle_rad)
                # 3. Translate
                pt[0], pt[1] = rx + cx + offset_x, ry + cy + offset_y
                
            context['live_math'] = [[int(pt[0]), int(pt[1])] for pt in dst_pts]
            
            # Stage 1 Override
            if stage == 'flat':
                start_x, start_y = dst_pts[0][0], dst_pts[0][1]
                flat_size = int(200 * scale)
                dst_pts = np.float32([[start_x, start_y], [start_x + flat_size, start_y], [start_x + flat_size, start_y + flat_size], [start_x, start_y + flat_size]])

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
            
            _, buffer = cv2.imencode('.jpg', base_img)
            context['image_url'] = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
            return render(request, 'upload.html', context)
        except Exception as e:
            context['error_message'] = str(e)
            return render(request, 'upload.html', context)
    return render(request, 'upload.html')

def landing_view(request):
    return render(request, 'landing.html')