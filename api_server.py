from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import uuid
import shutil
import threading
import asyncio
import base64
from detection_worker import VideoWorker
from comparison_worker import ComparisonWorker

app = FastAPI(title="Road Safety API")

# Allow CORS from frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS = {}
BASE_JOBS_DIR = os.path.join(os.getcwd(), 'api_jobs')
os.makedirs(BASE_JOBS_DIR, exist_ok=True)

@app.get('/')
async def root():
    return {"status": "ok", "message": "Road Safety API is running"}

@app.post('/upload')
async def upload_video(file: UploadFile = File(...)):
    print(f"[API] Upload request received: {file.filename}")
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(BASE_JOBS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    video_path = os.path.join(job_dir, 'input.mp4')
    
    try:
        with open(video_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        print(f"[API] Video saved: {video_path} ({len(content)} bytes)")
    except Exception as e:
        print(f"[API] Error saving video: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)
    
    # create worker and start background thread
    worker = VideoWorker(job_id, video_path, job_dir)
    JOBS[job_id] = worker.status

    def _run():
        print(f"[API] Starting worker for job {job_id}")
        worker.run()
        JOBS[job_id] = worker.status
        print(f"[API] Worker completed for job {job_id}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    print(f"[API] Returning job_id: {job_id}")
    return JSONResponse({'job_id': job_id})

@app.post('/upload_comparison')
async def upload_comparison(base_video: UploadFile = File(...), present_video: UploadFile = File(...)):
    print(f"[API] Comparison upload request received: {base_video.filename}, {present_video.filename}")
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(BASE_JOBS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    base_video_path = os.path.join(job_dir, 'base.mp4')
    present_video_path = os.path.join(job_dir, 'present.mp4')
    
    try:
        # Save base video
        with open(base_video_path, 'wb') as f:
            content = await base_video.read()
            f.write(content)
        print(f"[API] Base video saved: {base_video_path} ({len(content)} bytes)")
        
        # Save present video
        with open(present_video_path, 'wb') as f:
            content = await present_video.read()
            f.write(content)
        print(f"[API] Present video saved: {present_video_path} ({len(content)} bytes)")
    except Exception as e:
        print(f"[API] Error saving videos: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)
    
    # Create comparison worker
    worker = ComparisonWorker(job_id, base_video_path, present_video_path, job_dir)
    JOBS[job_id] = worker.status

    def _run():
        print(f"[API] Starting comparison worker for job {job_id}")
        worker.run()
        JOBS[job_id] = worker.status
        print(f"[API] Comparison worker completed for job {job_id}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    print(f"[API] Returning job_id: {job_id}")
    return JSONResponse({'job_id': job_id})

@app.get('/status/{job_id}')
def status(job_id: str):
    status = JOBS.get(job_id)
    if not status:
        return JSONResponse({'error': 'job not found'}, status_code=404)
    return status

@app.get('/frame/{job_id}')
def latest_frame(job_id: str):
    job_dir = os.path.join(BASE_JOBS_DIR, job_id)
    latest = os.path.join(job_dir, 'latest.jpg')
    if os.path.exists(latest):
        return FileResponse(latest, media_type='image/jpeg')
    return JSONResponse({'error': 'frame not available'}, status_code=404)


@app.websocket('/ws/{job_id}')
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    try:
        while True:
            status = JOBS.get(job_id)
            if not status:
                # send a simple status error once and sleep
                await websocket.send_json({'type': 'error', 'message': 'job not found'})
                await asyncio.sleep(1.0)
                continue

            # send status update
            try:
                await websocket.send_json({'type': 'status', 'status': status})
            except Exception:
                # client may have disconnected
                break

            # send latest frame if available
            latest = os.path.join(BASE_JOBS_DIR, job_id, 'latest.jpg')
            if os.path.exists(latest):
                try:
                    with open(latest, 'rb') as f:
                        data = f.read()
                    b64 = base64.b64encode(data).decode('ascii')
                    await websocket.send_json({'type': 'frame', 'data': b64})
                except Exception:
                    pass

            if status.get('completed'):
                # final status sent, then close
                break

            await asyncio.sleep(0.8)
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

@app.get('/results/{job_id}')
def results(job_id: str):
    job_dir = os.path.join(BASE_JOBS_DIR, job_id)
    results_path = os.path.join(job_dir, 'results.json')
    if os.path.exists(results_path):
        return FileResponse(results_path, media_type='application/json')
    status = JOBS.get(job_id)
    if status:
        return status
    return JSONResponse({'error': 'job not found'}, status_code=404)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
