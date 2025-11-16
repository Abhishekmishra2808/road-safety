# VisionX

**AI-Powered Road Change Detection Platform**

VisionX is an advanced computer vision system that compares two road surveillance videos (base and present) to automatically detect and analyze infrastructure changes, including new or removed traffic signs, road markings, potholes, and other road conditions.

![VisionX Logo](https://img.shields.io/badge/VisionX-Road%20Safety-black?style=for-the-badge)

---

## 🎯 Features

### Core Capabilities
- **Dual Video Comparison** - Upload base (reference) and present videos for intelligent comparison
- **Real-Time Detection** - Live frame-by-frame analysis with WebSocket updates
- **Change Analytics** - Comprehensive dashboard with charts, metrics, and insights
- **Infrastructure Focus** - Detects traffic signs, road markings, potholes (excludes vehicles)
- **AI-Powered** - Uses YOLOv8 deep learning model with custom detection algorithms

### Analytics Dashboard
- **Key Metrics** - Total additions, removals, and change severity assessment
- **Data Visualizations** - Bar charts and pie charts for change distribution
- **Top Changes Table** - Detailed breakdown of detected changes
- **Intelligent Insights** - Auto-generated findings and recommendations
- **Export Results** - Download complete analysis reports

---

## 🏗️ Architecture

### Tech Stack

**Backend (Python)**
- FastAPI - High-performance async web framework
- Uvicorn - ASGI server with WebSocket support
- PyTorch - Deep learning framework
- Ultralytics YOLOv8 - Object detection model
- OpenCV - Computer vision processing

**Frontend (React)**
- React 18.2 - Modern UI framework
- Vite - Fast build tool
- Recharts - Data visualization library
- Axios - HTTP client

### Project Structure
```
road-safety/
├── api_server.py           # FastAPI backend server
├── comparison_worker.py    # Video comparison engine
├── detection_worker.py     # Object detection worker (optional)
├── yolov8n.pt             # YOLOv8 trained model
├── requirements.txt        # Python dependencies
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── App.jsx        # Main application component
│   │   ├── ResultsAnalytics.jsx  # Analytics dashboard
│   │   ├── styles.css     # UJET-inspired minimalist design
│   │   └── main.jsx       # React entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── api_jobs/              # Temporary job storage (auto-created)
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- Node.js 16 or higher
- CUDA 11.8 (optional, for GPU acceleration)
- 8GB+ RAM recommended

### Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/Abhishekmishra2808/road-safety.git
cd road-safety
```

#### 2. Setup Python Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### 3. Setup Frontend
```bash
cd frontend
npm install
cd ..
```

### Running the Application

#### Start Backend Server (Terminal 1)
```bash
# Activate virtual environment first
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Start FastAPI server
uvicorn api_server:app --reload --port 8000 --host 0.0.0.0
```

Backend will be available at: `http://localhost:8000`

#### Start Frontend Server (Terminal 2)
```bash
cd frontend
npm run dev
```

Frontend will be available at: `http://localhost:3000`

#### Access the Application
Open your browser and navigate to: **http://localhost:3000**

---

## 📖 Usage Guide

### Step 1: Upload Videos
1. **Select Base Video** - Choose your reference/baseline road footage
2. **Select Present Video** - Choose the current road footage to compare
3. Click **"START COMPARISON"** button

### Step 2: Monitor Progress
- Watch real-time change detection feed
- Track progress with live frame count and percentage
- View quick stats of detected changes

### Step 3: Analyze Results
Once comparison is complete, you'll see:
- **Key Metrics Dashboard** - Total additions, removals, change severity
- **Bar Chart** - Category-wise breakdown of changes
- **Pie Chart** - Overall distribution of additions vs. removals
- **Top Changes Table** - Detailed list of significant changes
- **Insights & Recommendations** - AI-generated findings and action items

### Step 4: Export Results
Click **"DOWNLOAD RESULTS"** to get the complete analysis report with:
- Frame-by-frame comparison data
- Annotated detection images
- JSON data export

---

## 🔧 Configuration

### Backend Settings
Edit `api_server.py` to customize:
- `PORT` - Default: 8000
- `CORS_ORIGINS` - Allowed frontend origins
- `UPLOAD_DIR` - Job storage directory

### Detection Settings
Edit `comparison_worker.py` to adjust:
- `CONFIDENCE_THRESHOLD` - Default: 0.3
- `SKIP_FRAMES` - Frame sampling rate (default: process 2 fps)
- `SPATIAL_THRESHOLD` - Object matching distance (default: 50px)

### Frontend Settings
Edit `frontend/src/App.jsx` to change:
- `API_URL` - Backend server URL
- Chart colors and styling
- Severity thresholds

---

## 🎨 Design Philosophy

VisionX follows a **minimalist design language** inspired by UJET:
- Clean black and white color palette
- Bold typography with Inter font
- Wide letter spacing for branding
- Subtle animations and hover effects
- Focus on content and functionality

---

## 🤖 Detection Capabilities

### What VisionX Detects
✅ **Traffic Signs** - Stop signs, traffic lights, regulatory signs  
✅ **Road Markings** - Lane lines, crosswalks, road paint  
✅ **Potholes** - Road damage and surface defects  
✅ **Infrastructure** - Poles, barriers, road furniture  

### What VisionX Ignores
❌ Vehicles (cars, trucks, buses, motorcycles)  
❌ Boats  
❌ Persons and bicycles  

*Focus is exclusively on static infrastructure and road conditions*

---

## 📊 API Endpoints

### POST `/upload_comparison`
Upload two videos for comparison
- **Parameters**: 
  - `base_video` (file) - Reference video
  - `present_video` (file) - Current video
- **Returns**: `{ job_id: string }`

### WebSocket `/ws/{job_id}`
Real-time status updates
- **Sends**: Progress, frame count, detected changes
- **Format**: JSON messages

### GET `/results/{job_id}`
Download comparison results
- **Returns**: ZIP file with analysis data

---

## 🐛 Troubleshooting

### Backend Won't Start
- Ensure Python virtual environment is activated
- Check if port 8000 is available
- Verify all dependencies installed: `pip list`

### Frontend Won't Start
- Clear node_modules: `rm -rf node_modules && npm install`
- Check if port 3000 is available
- Verify Node.js version: `node --version` (should be 16+)

### CUDA/GPU Issues
- System will automatically fall back to CPU if CUDA unavailable
- Check CUDA installation: `python -c "import torch; print(torch.cuda.is_available())"`
- For CPU-only: Remove `--index-url` line from requirements.txt

### WebSocket Connection Fails
- Ensure backend is running on port 8000
- Check CORS settings in `api_server.py`
- Verify firewall isn't blocking WebSocket connections

---

## 🛠️ Development

### Run in Development Mode
```bash
# Backend with auto-reload
uvicorn api_server:app --reload --port 8000

# Frontend with hot-reload
cd frontend && npm run dev
```

### Build for Production
```bash
# Frontend production build
cd frontend
npm run build
# Output will be in frontend/dist/

# Serve frontend build
npm run preview
```

---

## 📝 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

**Abhishek Mishra**
- GitHub: [@Abhishekmishra2808](https://github.com/Abhishekmishra2808)

---

## 🙏 Acknowledgments

- **Ultralytics** - YOLOv8 object detection model
- **UJET** - Design inspiration
- **FastAPI** - Modern Python web framework
- **React** - UI library

---

## 📈 Future Enhancements

- [ ] Historical trend analysis
- [ ] Multi-camera support
- [ ] Custom object training
- [ ] Email notifications
- [ ] Cloud deployment guide
- [ ] Mobile responsive improvements
- [ ] Batch processing support

---

**VisionX** - *Intelligent Infrastructure Monitoring*
