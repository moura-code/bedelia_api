# 🚀 Quick Deploy to Railway (5 minutes)

Railway is the easiest way to deploy your API. Here's how:

## Step 1: Push to GitHub

```bash
cd /home/feijoes/Desktop/bedelias-scraper
git add .
git commit -m "feat: add deployment configuration"
git push origin main
```

## Step 2: Deploy on Railway

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click **"New Project"** → **"Deploy from GitHub repo"**
4. Select your repository: `bedelia_api`
5. Railway will detect your Dockerfile automatically

## Step 3: Add PostgreSQL Database

1. In your Railway project, click **"New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway automatically sets `DATABASE_URL` environment variable

## Step 4: Set Environment Variables

Go to your service → **Variables** tab, add:

```
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_ENVIRONMENT=production
DEBUG=False
ALLOWED_HOSTS=your-app-name.up.railway.app
```

**Generate a secret key:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Step 5: Run Migrations

1. Go to your service → **Settings** → **Deploy**
2. Add deploy command: `python manage.py migrate`
3. Or use Railway's CLI:
   ```bash
   railway run python manage.py migrate
   ```

## Step 6: Deploy!

Railway will automatically:
- ✅ Build your Docker container
- ✅ Deploy your API
- ✅ Provide HTTPS URL
- ✅ Auto-deploy on every git push

## Your API will be live at:
`https://your-app-name.up.railway.app/api/`

## Test it:
- API Schema: `https://your-app-name.up.railway.app/api/schema/`
- Swagger UI: `https://your-app-name.up.railway.app/api/schema/swagger-ui/`

---

## Alternative: Render.com

1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. New → Web Service
4. Connect your repo
5. Use these settings:
   - **Build Command**: `cd bedelia && pip install -r requirements.txt`
   - **Start Command**: `cd bedelia && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
6. Add PostgreSQL database
7. Set environment variables (same as Railway)

---

## Need Help?

See `DEPLOYMENT.md` for detailed instructions and troubleshooting.

