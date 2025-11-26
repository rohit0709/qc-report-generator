# QC Report Generator - Streamlit Cloud Deployment Guide

## Prerequisites
- GitHub account
- Your code pushed to a GitHub repository

## Step-by-Step Deployment

### 1. Prepare Your GitHub Repository

```bash
# Initialize git (if not already done)
cd "/Users/rohitranjan/Documents/Python Projects/QC Report AG"
git init

# Create .gitignore
echo "QC_Output/
__pycache__/
*.pyc
.DS_Store
*.pdf
*.xlsx
evaluation/
.gemini/" > .gitignore

# Add and commit files
git add .
git commit -m "Initial commit for QC Report Generator"

# Create GitHub repo and push
# (Create repo on github.com first, then run these commands)
git remote add origin https://github.com/YOUR_USERNAME/qc-report-generator.git
git branch -M main
git push -u origin main
```

### 2. Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Sign in with your GitHub account
3. Click "New app"
4. Fill in:
   - **Repository:** `YOUR_USERNAME/qc-report-generator`
   - **Branch:** `main`
   - **Main file path:** `qc_report_ag/app.py`
5. Click "Deploy"

### 3. Wait for Deployment
- First deployment takes 2-5 minutes
- You'll get a URL like: `https://qc-report-generator.streamlit.app`

### 4. Share Your App
- Send the URL to anyone who needs to use it
- No installation required on their end!

## Updating Your App

Whenever you make changes:
```bash
git add .
git commit -m "Description of changes"
git push
```

Streamlit Cloud will automatically redeploy within 1-2 minutes.

## Troubleshooting

**App won't start?**
- Check the logs in Streamlit Cloud dashboard
- Verify all files are committed to GitHub
- Check that `requirements.txt` has all dependencies

**App is slow?**
- Free tier has 1GB RAM limit
- App sleeps after inactivity (wakes in ~30 seconds)

**Need help?**
- Streamlit docs: https://docs.streamlit.io/streamlit-community-cloud
- Community forum: https://discuss.streamlit.io/

## Files Created for Deployment
- `.streamlit/config.toml` - App configuration
- `qc_report_ag/requirements.txt` - Python dependencies
- `DEPLOYMENT.md` - This file
