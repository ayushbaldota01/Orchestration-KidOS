# 🚀 KidOS Startup Guide

This document explains how to start all the required servers for the KidOS project. Since this app runs entirely offline using AI models on your own machine, you need to start three separate background services before using the web interface.

---

### Step 1: Start Ollama (Text Generation)
Ollama handles all of the reasoning and text generation (using the `qwen2.5:7b-instruct` model).

1. Open your terminal or command prompt.
2. Ensure Ollama is running in the background. If you have the Ollama app installed, usually it runs automatically on startup.
3. If it is not running, run the following command to start the server:
   ```cmd
   ollama serve
   ```
*(By default, Ollama runs on `http://127.0.0.1:11434`)*

---

### Step 2: Start ComfyUI (Image Generation)
ComfyUI handles all of the image generation (using Stable Diffusion 1.5).

1. Open a new terminal window or use your existing ComfyUI shortcut.
2. Navigate to the folder where you installed ComfyUI.
3. Run the ComfyUI server. Depending on how you installed it, you would typically run:
   ```cmd
   python main.py
   ```
   *or if you have a `.bat` file:*
   ```cmd
   run_nvidia_gpu.bat
   ```
*(By default, ComfyUI runs on `http://127.0.0.1:8188`. Keep this terminal window open in the background).*

---

### Step 3: Start the KidOS Backend Server
This is the Python web server (FastAPI) that bridges Ollama, ComfyUI, the TTS Voice system, and your frontend UI.

1. Open a new terminal window in your project's root directory (`h:\Orchestration Hall\ai-chatbot`).
2. Activate your Python virtual environment:
   ```cmd
   .\ai_env\Scripts\activate
   ```
3. Start the FastAPI server using Uvicorn:
   ```cmd
   python -m uvicorn kidos.api.main:app --reload --host 0.0.0.0 --port 8000
   ```
*(The server will run on `http://localhost:8000`)*

---

### ✨ Step 4: Open the Web App!
Once all three terminals are running without errors, open your web browser and go to:
👉 **[http://localhost:8000](http://localhost:8000)**

You should see the "Let's Go!" screen and all AI pipelines (Fact Feed, Story Library, WonderTV generation) should work flawlessly!
