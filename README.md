# BeSpoke | Your Customization Peer

BeSpoke is a high-performance web application designed for real-time product customization. It leverages **OpenCV** to perform advanced computer vision tasks, allowing users to map 2D designs onto 3D objects with physical realism.

## 🚀 Features
- **3D Perspective Mapping**: Uses Homography matrices to align designs with product angles.
- **Physics-Based UI**: A minimalist "Antigravity" inspired landing page with parallax effects.
- **Realistic Blending**: Grayscale shadow mapping to simulate fabric textures and folds.
- **High-Performance Rendering**: In-memory Base64 encoding to bypass disk I/O.
- **Interactive Controls**: Real-time scaling, rotation, and X/Y translation.

## 🛠️ Tech Stack
- **Backend**: Python, Django
- **Computer Vision**: OpenCV (CV2), NumPy
- **Frontend**: HTML5, CSS3 (Glassmorphism), Vanilla JavaScript

## 🔧 Installation
1. Clone the repo: `git clone https://github.com/asnamaryallen/BeSpoke_Studio.git`
2. Create environment: `python -m venv myenv`
3. Activate: `myenv\Scripts\activate`
4. Install: `pip install django opencv-python numpy`
5. Run: `python manage.py runserver`
