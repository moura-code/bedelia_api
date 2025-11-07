# 🚀 Quick Deploy with SQLite

Your API is now configured to use **SQLite by default** (simpler than PostgreSQL).

## ⚠️ Important: Django Cannot Be Static

**GitHub Pages only hosts static HTML/CSS/JS files** - it cannot run Django/Python applications.

Django needs a server to process requests. You have two options:

## ✅ Option 1: PythonAnywhere (Best for SQLite - FREE)

**Perfect for SQLite databases!**

### Steps:

1. **Sign up**: [pythonanywhere.com](https://www.pythonanywhere.com) (free account)

2. **Upload your code**:
   - Go to "Files" tab
   - Click "Upload a file" or use Git:
   ```bash
   git clone https://github.com/yourusername/bedelia_api.git
   ```

3. **Open Bash Console** and run:
   ```bash
   cd bedelia
   mkvirtualenv --python=/usr/bin/python3.10 bedelia
   pip install -r requirements.txt
   python manage.py migrate
   ```

4. **Create Web App**:
   - Go to "Web" tab
   - Click "Add a new web app"
   - Choose "Manual configuration" → "Python 3.10"
   - Source code: `/home/yourusername/bedelia`

5. **Edit WSGI file** (click the link):
   ```python
   import sys
   path = '/home/yourusername/bedelia'
   if path not in sys.path:
       sys.path.append(path)
   
   import os
   os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
   os.environ['USE_SQLITE'] = 'True'
   os.environ['DEBUG'] = 'False'
   os.environ['DJANGO_SECRET_KEY'] = 'your-secret-key-here'
   
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

6. **Reload** your web app

7. **Done!** Your API is live at: `https://yourusername.pythonanywhere.com/api/`

---

## ✅ Option 2: Railway (Also Free, Easy Setup)

Railway can also use SQLite, but PostgreSQL is recommended for production.

### Steps:

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "feat: configure SQLite for hosting"
   git push origin main
   ```

2. **Go to Railway**: [railway.app](https://railway.app)

3. **Deploy**:
   - New Project → Deploy from GitHub
   - Select your repo
   - Railway will auto-detect Dockerfile

4. **Set Environment Variables**:
   ```
   USE_SQLITE=True
   DJANGO_SECRET_KEY=your-secret-key
   DEBUG=False
   ALLOWED_HOSTS=your-app.up.railway.app
   ```

5. **Deploy Command** (in Settings → Deploy):
   ```
   python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
   ```

---

## 📝 SQLite Database in GitHub

You can commit your SQLite database to GitHub:

```bash
# After running migrations locally
git add bedelia/db.sqlite3
git commit -m "feat: add SQLite database"
git push
```

**Note**: Only commit if database is small (< 100MB). For larger databases, use PostgreSQL.

---

## 🔧 Current Configuration

Your project is configured to:
- ✅ Use SQLite by default (`USE_SQLITE=True`)
- ✅ Allow SQLite database in Git (`.gitignore` updated)
- ✅ Fall back to PostgreSQL if `USE_SQLITE=False`

To switch to PostgreSQL:
```bash
USE_SQLITE=False
DATABASE_URL=postgresql://...
```

---

## 🎯 Recommended: PythonAnywhere

**Why PythonAnywhere?**
- ✅ Free tier available
- ✅ SQLite works perfectly
- ✅ Persistent storage (database won't disappear)
- ✅ Easy setup
- ✅ No spin-down issues
- ✅ Custom domain support

**Get started in 5 minutes!**

1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com)
2. Follow the steps above
3. Your API will be live!

---

## 📚 More Info

See `STATIC_HOSTING.md` for detailed instructions and alternatives.

