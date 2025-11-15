"""
Streamlit web UI for road safety analysis.
Upload videos and view results in browser.
"""
import os
import sys
import streamlit as st
import subprocess
import json
import pandas as pd
import shutil


def _detect_compute_capabilities():
    """Check whether PyTorch and CUDA are available for GPU inference."""
    capabilities = {
        "torch_available": False,
        "cuda_available": False,
        "gpu_name": None
    }

    try:
        import torch

        capabilities["torch_available"] = True
        if torch.cuda.is_available():
            capabilities["cuda_available"] = True
            try:
                capabilities["gpu_name"] = torch.cuda.get_device_name(0)
            except Exception:
                capabilities["gpu_name"] = "CUDA Device 0"
    except ImportError:
        pass
    except Exception:
        # Any unexpected CUDA initialization error should not break the UI
        capabilities["torch_available"] = True

    return capabilities


COMPUTE_INFO = _detect_compute_capabilities()


# Page configuration
st.set_page_config(
    page_title="Road Safety Analysis",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        padding: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2ca02c;
        margin-top: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)


def save_uploaded_file(uploaded_file, save_path):
    """Save uploaded file to disk."""
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return save_path


def run_analysis_pipeline(base_video, present_video, output_dir, fps=1, max_pairs=20, device='cpu'):
    """
    Run the analysis pipeline.

    Args:
        base_video: Path to base video
        present_video: Path to present video
        output_dir: Output directory
        fps: Frames per second
        max_pairs: Max frame pairs to process
        device: Execution device for YOLO inference (e.g., 'cpu', '0')

    Returns:
        Dictionary containing pipeline status and metadata.
    """
    python_exe = sys.executable
    resolved_device = str(device or 'cpu')

    cmd = [
        python_exe,
        'run_pipeline_quick.py',
        base_video,
        present_video,
        output_dir,
        '--fps', str(fps),
        '--max-pairs', str(max_pairs),
        '--device', resolved_device
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            encoding='utf-8',
            errors='replace'
        )

        results_path = os.path.join(output_dir, 'results')
        return {
            "success": True,
            "results_dir": results_path,
            "output_dir": output_dir,
            "device": resolved_device,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except subprocess.CalledProcessError as e:
        error_msg = (
            f"Command failed with exit code {e.returncode}\n\nSTDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}"
        )
        return {
            "success": False,
            "results_dir": None,
            "output_dir": output_dir,
            "device": resolved_device,
            "error": error_msg,
            "stdout": e.stdout,
            "stderr": e.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "results_dir": None,
            "output_dir": output_dir,
            "device": resolved_device,
            "error": f"Unexpected error: {str(e)}",
            "stdout": None,
            "stderr": None
        }


def display_results(results_dir, pipeline_dirs=None, device_label=None, pipeline_logs=None, pipeline_warnings=None):
    """Display analysis results in Streamlit."""

    json_path = os.path.join(results_dir, 'analysis_results.json')
    csv_path = os.path.join(results_dir, 'changes.csv')
    evidence_dir = os.path.join(results_dir, 'evidence')

    json_results = []
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                json_results = json.load(f)
        except json.JSONDecodeError:
            st.error("Unable to read analysis_results.json. The file may be corrupted.")

    df = None
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:  # pylint: disable=broad-except
            st.error(f"Unable to read changes.csv: {exc}")

    if not json_results and df is None:
        st.warning("No results found. Analysis may have failed.")
        st.info("Please check that the pipeline completed successfully.")
        return

    aligned_dir = None
    if pipeline_dirs:
        aligned_dir = pipeline_dirs.get('aligned')

    evidence_files = []
    if os.path.exists(evidence_dir):
        evidence_files = sorted([
            f for f in os.listdir(evidence_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])

    st.markdown('<p class="sub-header">� Analysis Output</p>', unsafe_allow_html=True)
    if device_label:
        st.caption(f"Compute device: {device_label}")

    summary_tab, table_tab, gallery_tab, raw_tab = st.tabs([
        "Summary",
        "Changes Table",
        "Evidence Gallery",
        "Raw Data & Logs"
    ])

    with summary_tab:
        if json_results:
            total_pairs = len(json_results)
            total_matched = sum(len(r.get('matched_objects', [])) for r in json_results)
            total_missing = sum(len(r.get('missing_objects', [])) for r in json_results)
            total_new = sum(len(r.get('new_objects', [])) for r in json_results)
            avg_ssim = sum(r.get('overall_ssim', 0) for r in json_results) / max(total_pairs, 1)

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Frame Pairs", total_pairs)
            col2.metric("Matched Objects", total_matched)
            col3.metric("Missing Objects", total_missing)
            col4.metric("New Objects", total_new)
            col5.metric("Avg SSIM", f"{avg_ssim:.3f}")

        if df is not None and not df.empty:
            st.markdown('---')
            col1, col2, col3, col4 = st.columns(4)

            severe_count = int((df['severity'] == 'SEVERE').sum()) if 'severity' in df.columns else 0
            new_count = int((df['severity'] == 'NEW').sum()) if 'severity' in df.columns else 0

            notes_series = df['notes'].fillna('') if 'notes' in df.columns else pd.Series(dtype=str)
            missing_count = int(notes_series.str.contains('missing', case=False).sum())

            col1.metric("Total Changes", len(df))
            col2.metric("Severe Changes", severe_count)
            col3.metric("Missing Elements", missing_count)
            col4.metric("New Elements", new_count)

            st.markdown('<p class="sub-header">🔍 Changes by Severity</p>', unsafe_allow_html=True)
            severity_counts = df['severity'].value_counts() if 'severity' in df.columns else pd.Series(dtype=int)

            chart_col, table_col = st.columns(2)
            if not severity_counts.empty:
                chart_col.bar_chart(severity_counts)
                table_col.dataframe(
                    severity_counts.reset_index().rename(columns={'index': 'Severity', 'severity': 'Count'}),
                    use_container_width=True
                )
            else:
                chart_col.info("No severity data available.")
                table_col.empty()

            st.markdown('<p class="sub-header">📦 Changes by Element Type</p>', unsafe_allow_html=True)
            if 'element_type' in df.columns:
                element_counts = df['element_type'].value_counts()
                if not element_counts.empty:
                    st.bar_chart(element_counts)
                else:
                    st.info("No element type information available.")
            else:
                st.info("Element type column not found in report.")

        if evidence_files:
            st.markdown('<p class="sub-header">📸 Detection Preview</p>', unsafe_allow_html=True)
            preview_path = os.path.join(evidence_dir, evidence_files[0])
            st.image(preview_path, caption=evidence_files[0], use_column_width=True)
        elif not (df is not None and not df.empty):
            st.info("No evidence images were generated for this run.")

    with table_tab:
        if df is None or df.empty:
            st.info("No tabular report generated. This usually means no significant changes were detected.")
        else:
            severity_options = sorted(df['severity'].dropna().unique()) if 'severity' in df.columns else []
            selected_severities = st.multiselect(
                'Filter by Severity',
                options=severity_options,
                default=severity_options
            )

            filtered_df = df
            if selected_severities:
                filtered_df = filtered_df[filtered_df['severity'].isin(selected_severities)]

            st.dataframe(
                filtered_df,
                use_container_width=True,
                height=400
            )

            st.download_button(
                label="📥 Download Full CSV Report",
                data=df.to_csv(index=False),
                file_name="road_safety_report.csv",
                mime="text/csv",
                use_container_width=True
            )

    with gallery_tab:
        if not evidence_files and not aligned_dir:
            st.info("No visual artefacts generated for this run.")
        else:
            gallery_tabs = st.tabs(["Detections", "Aligned Frame Pairs"])

            with gallery_tabs[0]:
                if evidence_files:
                    default_index = 0
                    selected_idx = st.slider(
                        "Evidence image index",
                        min_value=1,
                        max_value=len(evidence_files),
                        value=1
                    )
                    selected_image = evidence_files[selected_idx - 1]
                    image_path = os.path.join(evidence_dir, selected_image)
                    st.image(image_path, caption=selected_image, use_column_width=True)
                else:
                    st.info("No detection evidence images available.")

            with gallery_tabs[1]:
                if aligned_dir and os.path.exists(aligned_dir):
                    base_frames = sorted(
                        [f for f in os.listdir(aligned_dir) if f.startswith('base_') and f.lower().endswith(('.jpg', '.png'))]
                    )
                    present_frames = sorted(
                        [f for f in os.listdir(aligned_dir) if f.startswith('present_') and f.lower().endswith(('.jpg', '.png'))]
                    )
                    frame_count = min(len(base_frames), len(present_frames))

                    if frame_count:
                        frame_idx = st.slider(
                            "Aligned frame pair",
                            min_value=1,
                            max_value=frame_count,
                            value=1
                        )
                        base_path = os.path.join(aligned_dir, base_frames[frame_idx - 1])
                        present_path = os.path.join(aligned_dir, present_frames[frame_idx - 1])

                        col_a, col_b = st.columns(2)
                        col_a.image(base_path, caption=base_frames[frame_idx - 1], use_column_width=True)
                        col_b.image(present_path, caption=present_frames[frame_idx - 1], use_column_width=True)
                    else:
                        st.info("Aligned frames not available for preview.")
                else:
                    st.info("Aligned frame directory not found. Re-run the analysis to refresh frames.")

    with raw_tab:
        if json_results:
            st.markdown("**Sample from analysis_results.json**")
            sample_count = min(len(json_results), 3)
            st.json(json_results[:sample_count])

            with open(json_path, 'r') as f:
                st.download_button(
                    label="📥 Download JSON Results",
                    data=f.read(),
                    file_name="analysis_results.json",
                    mime="application/json",
                    use_container_width=True
                )
        else:
            st.info("JSON summary not available.")

        pdf_path = os.path.join(results_dir, 'summary.pdf')
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                st.download_button(
                    label="📥 Download PDF Summary",
                    data=f,
                    file_name="road_safety_summary.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        if pipeline_logs:
            with st.expander("Pipeline console output"):
                st.code(pipeline_logs, language="text")

        if pipeline_warnings:
            with st.expander("Pipeline warnings / stderr"):
                st.code(pipeline_warnings, language="text")


def main():
    # Header
    st.markdown('<p class="main-header">🚗 Road Safety Analysis System</p>', unsafe_allow_html=True)
    st.markdown('---')
    
    # Default device selection
    device_flag = 'cpu'
    device_label = 'CPU'

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("Upload Videos")
        base_video = st.file_uploader(
            "Base Video (Before)",
            type=['mp4', 'avi', 'mov'],
            help="Upload the baseline/before video"
        )
        
        present_video = st.file_uploader(
            "Present Video (After)",
            type=['mp4', 'avi', 'mov'],
            help="Upload the present/after video"
        )
        
        st.subheader("Analysis Settings")
        
        fps = st.slider(
            "Frames per Second",
            min_value=0.5,
            max_value=5.0,
            value=1.0,
            step=0.5,
            help="Number of frames to extract per second"
        )
        
        max_pairs = st.slider(
            "Max Frame Pairs",
            min_value=5,
            max_value=100,
            value=20,
            step=5,
            help="Maximum number of frame pairs to analyze (for quick testing)"
        )

        st.subheader("Compute Device")
        cuda_available = COMPUTE_INFO.get("cuda_available", False)
        gpu_name = COMPUTE_INFO.get("gpu_name")

        if cuda_available:
            device_choices = [
                ("Auto (prefer GPU)", "0"),
                ("GPU only", "0"),
                ("CPU (compatibility)", "cpu")
            ]
        else:
            device_choices = [
                ("Auto (CPU fallback)", "cpu"),
                ("CPU only", "cpu")
            ]

        device_labels = [choice[0] for choice in device_choices]
        default_index = 0
        selected_label = st.selectbox(
            "Compute Device",
            device_labels,
            index=default_index,
            help="Select GPU acceleration when available. Auto mode prefers GPU but falls back to CPU if needed."
        )

        for label_option, flag in device_choices:
            if label_option == selected_label:
                device_flag = flag if cuda_available or flag == 'cpu' else 'cpu'
                break

        if device_flag != 'cpu' and cuda_available:
            device_label = f"GPU ({gpu_name or 'device 0'})"
            st.caption(f"Detected GPU: {gpu_name or 'device 0'}")
        elif device_flag == 'cpu' and cuda_available and selected_label.startswith('Auto'):
            device_label = "CPU (GPU temporarily unavailable)"
            st.caption("GPU detected but auto mode may fall back to CPU if busy.")
        elif device_flag == 'cpu' and cuda_available:
            device_label = "CPU"
            st.caption("Running on CPU by request.")
        else:
            device_label = "CPU"
            st.caption("No CUDA GPU detected. Using CPU.")
        
        analyze_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)
    
    # Main content area
    if base_video and present_video:
        
        if analyze_button:
            # Create persistent directory for this session (not temp)
            session_dir = os.path.join(os.getcwd(), 'streamlit_temp')
            os.makedirs(session_dir, exist_ok=True)
            
            st.info("🔄 Processing videos... This may take several minutes.")
            
            # Progress indicators
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Save uploaded videos
            status_text.text("📥 Saving uploaded videos...")
            progress_bar.progress(10)
            
            base_path = os.path.join(session_dir, 'base_video.mp4')
            present_path = os.path.join(session_dir, 'present_video.mp4')
            
            save_uploaded_file(base_video, base_path)
            save_uploaded_file(present_video, present_path)
            
            # Run analysis
            status_text.text(f"🔬 Running analysis pipeline on {device_label}...")
            progress_bar.progress(30)
            
            output_dir = os.path.join(session_dir, 'output')

            st.session_state['analysis_complete'] = False
            st.session_state['pipeline_logs'] = None
            st.session_state['pipeline_warnings'] = None

            pipeline_result = run_analysis_pipeline(
                base_path,
                present_path,
                output_dir,
                fps,
                max_pairs,
                device=device_flag
            )

            progress_bar.progress(90)

            if pipeline_result.get('success'):
                temp_results = os.path.join(output_dir, 'results')
                if os.path.exists(temp_results):
                    persistent_dir = os.path.join(os.getcwd(), 'streamlit_results')
                    if os.path.exists(persistent_dir):
                        shutil.rmtree(persistent_dir)
                    shutil.copytree(temp_results, persistent_dir)
                    results_dir = persistent_dir

                    status_text.text("✅ Analysis complete!")
                    progress_bar.progress(100)

                    st.success("✅ Analysis completed successfully!")

                    actual_device_flag = pipeline_result.get('device', device_flag)
                    if actual_device_flag != 'cpu' and COMPUTE_INFO.get('cuda_available'):
                        actual_device_label = f"GPU ({COMPUTE_INFO.get('gpu_name') or 'device 0'})"
                    elif actual_device_flag != 'cpu':
                        actual_device_label = f"Device {actual_device_flag}"
                    elif device_flag != 'cpu' and COMPUTE_INFO.get('cuda_available'):
                        actual_device_label = "CPU (GPU fallback)"
                    else:
                        actual_device_label = "CPU"

                    st.session_state['results_dir'] = results_dir
                    st.session_state['analysis_complete'] = True
                    st.session_state['pipeline_dirs'] = {
                        'base_frames': os.path.join(output_dir, 'base_frames'),
                        'present_frames': os.path.join(output_dir, 'present_frames'),
                        'aligned': os.path.join(output_dir, 'aligned')
                    }
                    st.session_state['device_label'] = actual_device_label
                    st.session_state['pipeline_logs'] = pipeline_result.get('stdout')
                    stderr_output = pipeline_result.get('stderr')
                    st.session_state['pipeline_warnings'] = stderr_output if stderr_output else None

                    # Cleanup temp videos (keep results and frame artefacts)
                    try:
                        if os.path.exists(base_path):
                            os.remove(base_path)
                        if os.path.exists(present_path):
                            os.remove(present_path)
                    except Exception:
                        pass  # Ignore cleanup errors
                else:
                    status_text.text("❌ Analysis failed")
                    st.error("❌ Results directory not found. Pipeline may have failed.")
                    error_msg = pipeline_result.get('error') or "Pipeline finished without producing results."
                    with st.expander("📋 Error Details (Click to expand)"):
                        st.code(error_msg, language="text")
            else:
                status_text.text("❌ Analysis failed")
                error_msg = pipeline_result.get('error') or "Analysis failed. Please review the logs."
                st.error("❌ Analysis failed. Please check your videos and try again.")
                with st.expander("📋 Error Details (Click to expand)"):
                    st.code(error_msg, language="text")

                stdout_output = pipeline_result.get('stdout')
                stderr_output = pipeline_result.get('stderr')
                if stdout_output:
                    with st.expander("ℹ️ Pipeline stdout"):
                        st.code(stdout_output, language="text")
                if stderr_output:
                    with st.expander("⚠️ Pipeline stderr"):
                        st.code(stderr_output, language="text")
        
        # Display results if available
        if st.session_state.get('analysis_complete', False):
            results_dir = st.session_state.get('results_dir')
            if results_dir and os.path.exists(results_dir):
                display_results(
                    results_dir,
                    pipeline_dirs=st.session_state.get('pipeline_dirs'),
                    device_label=st.session_state.get('device_label'),
                    pipeline_logs=st.session_state.get('pipeline_logs'),
                    pipeline_warnings=st.session_state.get('pipeline_warnings')
                )
    
    else:
        # Instructions
        st.info("👈 Please upload both base and present videos in the sidebar to begin analysis.")
        
        st.markdown("""
        ### 📖 How to Use
        
        1. **Upload Videos**: Upload your base (before) and present (after) road videos in the sidebar
    2. **Configure Settings**: Adjust FPS, max frame pairs, and preferred compute device
        3. **Run Analysis**: Click the "Run Analysis" button
        4. **View Results**: Review the analysis summary, detailed changes, and evidence images
        5. **Download Reports**: Download CSV and PDF reports for documentation
        
        ### 🔍 What Gets Analyzed
        
        - **Road Elements**: Traffic signs, poles, road markings, barriers
        - **Road Conditions**: Potholes, surface damage, wear patterns
        - **Change Detection**: Missing, new, moved, or damaged elements
        - **Severity Scoring**: Automatic classification of change severity
        
        ### 📊 Output Reports
        
        - **Evidence Images**: Side-by-side annotated comparisons with bounding boxes
        - **CSV Report**: Detailed list of all detected changes with metrics
        - **PDF Summary**: Executive summary with top issues and visualizations
        
        ### ⚡ Performance Tips
        
        - Use lower FPS (0.5-1) for faster processing
        - Reduce max frame pairs for quick tests
    - Enable GPU acceleration from the sidebar when a compatible device is detected
        - Keep video resolution moderate for best performance
        """)
        
        # System info
        with st.expander("🖥️ System Information"):
            st.write(f"Python: {sys.version}")
            st.write(f"Working Directory: {os.getcwd()}")
            
            try:
                import torch
                st.write(f"PyTorch: {torch.__version__}")
                st.write(f"CUDA Available: {torch.cuda.is_available()}")
                if torch.cuda.is_available():
                    st.write(f"GPU: {torch.cuda.get_device_name(0)}")
            except ImportError:
                st.write("PyTorch: Not installed")


if __name__ == "__main__":
    main()
