# Deployment Guide for Bedelias API

This guide will help you deploy your Django API to various hosting platforms.

## 🚀 Quick Deploy Options

### Option 1: Railway (Recommended - Easiest)

**Railway** offers a free tier and is very easy to use.

#### Steps:

1. **Sign up**: Go to [railway.app](https://railway.app) and sign up with GitHub

2. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Add PostgreSQL Database**:
   - Click "New" → "Database" → "PostgreSQL"
   - Railway will automatically set `DATABASE_URL`

4. **Configure Environment Variables**:
   Go to your service → Variables, and add:
   ```
   DJANGO_SECRET_KEY=your-secret-key-here
   DJANGO_ENVIRONMENT=production
   DEBUG=False
   ALLOWED_HOSTS=your-app-name.up.railway.app
   ```

5. **Deploy**:
   - Railway will automatically detect the Dockerfile and deploy
   - Or it will use the `railway.json` configuration

6. **Run Migrations**:
   - Go to your service → Settings → Deploy
   - Add a deploy command: `python manage.py migrate`

**Railway automatically provides:**
- HTTPS/SSL
- Automatic deployments on git push
- PostgreSQL database
- Environment variables management

---

### Option 2: Render (Free Tier Available)

**Render** offers a free tier with some limitations.

#### Steps:

1. **Sign up**: Go to [render.com](https://render.com) and sign up with GitHub

2. **Create New Web Service**:
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select the repository and branch

3. **Configure Build Settings**:
   ```
   Build Command: cd bedelia && pip install -r requirements.txt
   Start Command: cd bedelia && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
   ```

4. **Add PostgreSQL Database**:
   - Click "New" → "PostgreSQL"
   - Note the connection string

5. **Set Environment Variables**:
   ```
   DJANGO_SECRET_KEY=your-secret-key
   DJANGO_ENVIRONMENT=production
   DEBUG=False
   DATABASE_URL=postgresql://... (from PostgreSQL service)
   ALLOWED_HOSTS=your-app.onrender.com
   ```

6. **Deploy**:
   - Render will automatically deploy
   - First deployment may take a few minutes

**Note**: Free tier on Render spins down after 15 minutes of inactivity.

---

### Option 3: Fly.io (Good Free Tier)

**Fly.io** offers a generous free tier.

#### Steps:

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login**:
   ```bash
   fly auth login
   ```

3. **Create App**:
   ```bash
   cd bedelia
   fly launch
   ```

4. **Add PostgreSQL**:
   ```bash
   fly postgres create --name bedelias-db
   fly postgres attach bedelias-db
   ```

5. **Set Secrets**:
   ```bash
   fly secrets set DJANGO_SECRET_KEY=your-secret-key
   fly secrets set DJANGO_ENVIRONMENT=production
   fly secrets set DEBUG=False
   ```

6. **Deploy**:
   ```bash
   fly deploy
   ```

---

## 🔧 Pre-Deployment Checklist

Before deploying, make sure:

- [ ] All environment variables are set
- [ ] `DEBUG=False` in production
- [ ] `ALLOWED_HOSTS` includes your domain
- [ ] Database migrations are ready
- [ ] Static files are configured (if needed)
- [ ] CORS settings are configured
- [ ] Secret key is generated and secure

## 🔐 Environment Variables

You'll need to set these environment variables on your hosting platform:

### Required:
```bash
DJANGO_SECRET_KEY=your-secret-key-here  # Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DJANGO_ENVIRONMENT=production
DEBUG=False
ALLOWED_HOSTS=your-domain.com
```

### Database (usually auto-provided):
```bash
DATABASE_URL=postgresql://user:password@host:port/dbname
# OR individual variables:
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=bedelias-api
DB_HOST=host
DB_PORT=5432
```

### Optional:
```bash
CORS_ALLOWED_ORIGINS=https://your-frontend.com
```

## 📝 Post-Deployment Steps

1. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

2. **Create Superuser** (if needed):
   ```bash
   python manage.py createsuperuser
   ```

3. **Collect Static Files** (if using static files):
   ```bash
   python manage.py collectstatic --noinput
   ```

4. **Load Initial Data** (if you have fixtures):
   ```bash
   python manage.py loaddata initial_data.json
   ```

## 🧪 Testing Your Deployment

After deployment, test these endpoints:

- Health check: `https://your-domain.com/api/`
- API Schema: `https://your-domain.com/api/schema/`
- API Docs: `https://your-domain.com/api/schema/swagger-ui/`

## 🔄 Continuous Deployment

Most platforms support automatic deployments:

- **Railway**: Automatic on push to main branch
- **Render**: Automatic on push to main branch (configurable)
- **Fly.io**: Run `fly deploy` or set up GitHub Actions

## 📊 Monitoring

Consider setting up:

- Error tracking (Sentry)
- Uptime monitoring (UptimeRobot)
- Log aggregation (if platform provides)

## 🆘 Troubleshooting

### Database Connection Issues
- Check `DATABASE_URL` or individual DB variables
- Verify database is running and accessible
- Check firewall/network settings

### Static Files Not Loading
- Run `collectstatic`
- Check `STATIC_ROOT` and `STATIC_URL` settings
- Verify WhiteNoise is configured (already in requirements.txt)

### CORS Errors
- Set `CORS_ALLOWED_ORIGINS` with your frontend URL
- Or temporarily allow all origins for testing: `CORS_ALLOW_ALL_ORIGINS=True`

### 500 Errors
- Check logs on your hosting platform
- Verify `DEBUG=False` in production
- Check that all environment variables are set

## 🔗 Useful Links

- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Railway Docs](https://docs.railway.app/)
- [Render Docs](https://render.com/docs)
- [Fly.io Docs](https://fly.io/docs/)

