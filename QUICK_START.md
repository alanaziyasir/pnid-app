# Quick Start Guide

## 🚀 Start Both Servers

### Terminal 1: Frontend
```powershell
cd frontend
npm run dev --silent
```
✅ Frontend running at: **http://localhost:3000**

### Terminal 2: Backend
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```
✅ Backend API running at: **http://localhost:8000**  
✅ API Docs available at: **http://localhost:8000/docs**

## 📖 Usage

### 1. Upload P&ID Image
1. Open **http://localhost:3000**
2. Click **"Upload file"** or **drag & drop** your P&ID image
3. Wait for upload (progress bar → "Uploaded" ✓)

### 2. Configure & Analyze
1. Click **"Configure"** button
2. You'll be redirected to `/analysis` page
3. Image is **automatically preprocessed** in background
4. Check browser console for: `✅ Image preprocessed`

### 3. View Processed Files
Processed files are saved in:
```
backend/uploads/processed/
├── {filename}_processed.png  # Enhanced image
├── {filename}_binary.png     # Binary preview
└── {filename}_meta.json      # Metadata
```

## 🔍 Testing API Directly

### Check Status
```powershell
curl http://localhost:8000/api/process/status
```

### Upload File
```powershell
curl -X POST http://localhost:8000/api/upload `
  -F "file=@path/to/your/image.png"
```

### Process Image
```powershell
curl -X POST http://localhost:8000/api/process/preprocess `
  -H "Content-Type: application/json" `
  -d '{"filename": "your-uploaded-file.png"}'
```

## 🛠️ Troubleshooting

### Frontend won't start
```powershell
cd frontend
npm install
npm run dev
```

### Backend won't start
```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### CORS Errors
- Make sure backend is running on port 8000
- Make sure frontend is running on port 3000
- Check browser console for specific error

### Processing Errors
- Check that Pillow is installed: `pip show pillow`
- Verify file was uploaded successfully
- Check backend terminal for error logs

## 📊 What to Expect

### Main Page
- Clean, professional UI
- Upload area with drag & drop
- File preview with horizontal scroll
- Fullscreen view option
- "Configure" button to proceed

### Analysis Page
- **Left Panel**: ALLAM AI model selector
- **Right Panel**: Your uploaded image
- **Bottom**: Summary section with components and detected texts

### Backend Processing
- Automatic on "Configure" click
- Takes ~1-2 seconds for typical images
- Outputs saved in `uploads/processed/`

## 🎯 Key Features

✅ File upload with drag & drop  
✅ Progress indicator  
✅ Image preview with scroll  
✅ Fullscreen view  
✅ Automatic preprocessing  
✅ Beautiful, professional UI  
✅ RESTful API  
✅ Real-time updates  

## 📝 Notes

- **Image Formats**: PNG, JPEG, GIF, WebP
- **Max File Size**: No limit (adjust in backend if needed)
- **Processing Time**: ~1-2 seconds per image
- **Storage**: Files stored in `backend/uploads/`

---

**Ready to use!** 🎉

Just start both servers and open http://localhost:3000
