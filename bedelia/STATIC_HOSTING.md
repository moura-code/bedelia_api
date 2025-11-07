# Static Hosting with SQLite

## ⚠️ Important Note

**Django APIs cannot run as static sites.** Django is a dynamic web framework that requires a server (WSGI/ASGI) to process requests.

GitHub Pages only hosts static HTML/CSS/JS files - it cannot run Python/Django applications.

## ✅ Solution: Free Hosting with SQLite

Instead, use a free hosting service that supports Django with SQLite. Here are the best options:

### Option 1: PythonAnywhere (Recommended for SQLite)

**Free tier available** - Perfect for SQLite databases!

#### Steps:

1. **Sign up**: Go to [pythonanywhere.com](https://www.pythonanywhere.com) (free account)

2. **Upload your code**:
   - Go to "Files" tab
   - Upload your `bedelia` folder
   - Or use Git: `git clone https://github.com/yourusername/bedelia_api.git`

3. **Set up virtual environment**:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 bedelia
   pip install -r requirements.txt
   ```

4. **Configure database**:
   - SQLite will work automatically
   - Database file will be at: `/home/yourusername/bedelia/db.sqlite3`

5. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

6. **Create web app**:
   - Go to "Web" tab
   - Click "Add a new web app"
   - Choose "Manual configuration" → "Python 3.10"
   - Set source code: `/home/yourusername/bedelia`
   - Set WSGI file: `/var/www/yourusername_pythonanywhere_com_wsgi.py`

7. **Edit WSGI file**:
   ```python
   import sys
   path = '/home/yourusername/bedelia'
   if path not in sys.path:
       sys.path.append(path)
   
   import os
   os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
   
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

8. **Set environment variables**:
   - In WSGI file or via "Web" → "Environment variables":
     ```
     DJANGO_SECRET_KEY=your-secret-key
     DEBUG=False
     USE_SQLITE=True
     ```

9. **Reload web app**:
   - Click "Reload" button
   - Your API will be live at: `https://yourusername.pythonanywhere.com`

**Free tier includes:**
- ✅ SQLite database support
- ✅ 512MB disk space
- ✅ 100 seconds CPU time/day
- ✅ Custom subdomain
- ✅ HTTPS

---

### Option 2: Fly.io (Free Tier)

Fly.io supports SQLite and has a generous free tier.

#### Steps:

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login**:
   ```bash
   fly auth login
   ```

3. **Create app**:
   ```bash
   cd bedelia
   fly launch
   ```

4. **Set environment variables**:
   ```bash
   fly secrets set DJANGO_SECRET_KEY=your-secret-key
   fly secrets set USE_SQLITE=True
   fly secrets set DEBUG=False
   ```

5. **Deploy**:
   ```bash
   fly deploy
   ```

**Note**: Fly.io uses ephemeral storage, so SQLite data may be lost on restart. Consider using Fly volumes for persistence.

---

### Option 3: Render (Free Tier)

Render supports SQLite but with limitations.

#### Steps:

1. Go to [render.com](https://render.com)
2. New → Web Service
3. Connect GitHub repo
4. Settings:
   - **Build Command**: `cd bedelia && pip install -r requirements.txt`
   - **Start Command**: `cd bedelia && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
5. Environment variables:
   ```
   USE_SQLITE=True
   DJANGO_SECRET_KEY=your-secret-key
   DEBUG=False
   ```

**Note**: Render's free tier spins down after 15 minutes of inactivity, which may cause SQLite locking issues.

---

## 📝 Configuration

Your project is already configured to use SQLite by default. The setting is in `config/settings.py`:

```python
USE_SQLITE = os.environ.get("USE_SQLITE", "True").lower() == "true"
```

To use PostgreSQL instead, set:
```bash
USE_SQLITE=False
DATABASE_URL=postgresql://...
```

## 🗄️ SQLite Database in GitHub

You can commit your SQLite database to GitHub:

1. **Add to repository**:
   ```bash
   git add bedelia/db.sqlite3
   git commit -m "feat: add SQLite database"
   git push
   ```

2. **Note**: 
   - SQLite files can be large
   - Only commit if the database is small (< 100MB)
   - For larger databases, use PostgreSQL or external storage

3. **Update .gitignore** (already done):
   - `db.sqlite3` is NOT ignored (commented out)
   - `db.sqlite3-journal` is ignored (temporary files)

## 🚀 Quick Start with PythonAnywhere

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "feat: configure for SQLite hosting"
   git push origin main
   ```

2. **On PythonAnywhere**:
   - Clone your repo
   - Set up virtual environment
   - Run migrations
   - Configure web app
   - Done!

## ⚠️ Limitations of SQLite

- **Concurrent writes**: SQLite handles concurrent reads well, but writes can lock
- **File size**: Not ideal for very large databases (> 100GB)
- **Network file systems**: May have issues on network-mounted storage
- **Backup**: Need to backup the file regularly

For production with high traffic, consider PostgreSQL.

## 🔄 Alternative: Static JSON API

If you truly need a static site, you would need to:

1. Export your Django data to JSON files
2. Create a static site generator (like Jekyll, Hugo, or Next.js)
3. Serve JSON files as static assets
4. This requires a complete rewrite and loses dynamic features

This is not recommended unless you have specific requirements.

---

## 📚 Recommended: PythonAnywhere

For SQLite hosting, **PythonAnywhere is the best choice** because:
- ✅ Free tier available
- ✅ SQLite works perfectly
- ✅ Easy setup
- ✅ Persistent storage
- ✅ Custom domain support
- ✅ No spin-down issues

