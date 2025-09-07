# Pixel Banana Suite

A tiny dev suite to turn single sprites/source images into edited/animated assets using a FastAPI backend (with ComfyUI integration planned) and a Vite/React frontend.

## Quick Start

### Backend Setup


### Frontend Setup


Visit http://localhost:5173 to see the app.

## Project Structure


## API Endpoints

- `GET /pipeline/ping` - Health check
- `GET /pipeline/roots` - Check input/output directories
- `GET /pipeline/status` - Get recent jobs
- `POST /pipeline/poses` - Generate sprite poses
- `POST /edit` - Edit sprites (Nano Banana)
- `POST /animate` - Create animations
- `POST /agent/chat` - Chat assistant

## Features

- ✅ Fast backend with stub implementations
- ✅ CORS properly configured
- ✅ Windows path normalization
- ✅ Dark theme UI with Tailwind
- ✅ Backend health monitoring
- ✅ Job tracking system
- ✅ Chat assistant interface
- ✅ Quick action cards
- 🚧 ComfyUI integration (planned)
- 🚧 Real Gemini-powered edits (planned)

## Development Notes

### Port Configuration

If port 8000 is busy, you can use 8001:


### CORS

The backend allows requests from:
- http://localhost:5173
- http://127.0.0.1:5173
- http://localhost:5174
- http://127.0.0.1:5174

### Environment Variables

Backend `.env` file supports:
- `GEMINI_API_KEY` - For Nano Banana edits
- `GOOGLE_API_KEY` - Optional
- `COMFY_BASE` - ComfyUI server URL
- `COMFY_OUT` - ComfyUI output directory

## CLI Scripts


## Troubleshooting

### Backend unreachable
- Check the red banner in the UI for the exact error
- Ensure backend is running on the correct port
- Verify the API base URL in the browser console logs

### CORS errors
- Backend must be started before making requests
- Check that CORS middleware is added before routers
- Verify the origin URLs match exactly

### Windows path issues
- All paths are normalized to forward slashes
- The backend handles both formats automatically

## License

MIT