# Heroku Deployment Guide

## Prerequisites

1. Heroku CLI installed
2. Git repository initialized
3. Heroku account created

## Step 1: Create Heroku App

```bash
heroku login
heroku create tramper-api
```

## Step 2: Add Heroku Add-ons

```bash
# PostgreSQL database
heroku addons:create heroku-postgresql:mini

# Redis (for caching)
heroku addons:create heroku-redis:mini
```

## Step 3: Configure Environment Variables

```bash
# Django settings
heroku config:set DJANGO_SETTINGS_MODULE=config.production
heroku config:set SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS=tramper-api.herokuapp.com

# Frontend URL
heroku config:set FRONTEND_URL=https://your-frontend-domain.com

# CORS
heroku config:set CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
heroku config:set CSRF_TRUSTED_ORIGINS=https://tramper-api.herokuapp.com,https://your-frontend-domain.com

# Mailgun Email Configuration
heroku config:set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
heroku config:set EMAIL_HOST=smtp.mailgun.org
heroku config:set EMAIL_PORT=587
heroku config:set EMAIL_USE_TLS=True
heroku config:set EMAIL_HOST_USER=postmaster@your-domain.mailgun.org
heroku config:set EMAIL_HOST_PASSWORD=your-mailgun-smtp-password
heroku config:set DEFAULT_FROM_EMAIL=noreply@tramper.com
heroku config:set SERVER_EMAIL=server@tramper.com
```

## Step 4: Deploy

```bash
git add .
git commit -m "Configure for Heroku deployment"
git push heroku main
```

## Step 5: Run Migrations

```bash
heroku run python manage.py migrate
```

## Step 6: Create Superuser

```bash
heroku run python manage.py createsuperuser
```

## Step 7: Verify Deployment

```bash
heroku open
```

Visit:

- API: https://tramper-api.herokuapp.com/
- Swagger Docs: https://tramper-api.herokuapp.com/api/docs/
- Admin: https://tramper-api.herokuapp.com/admin/

## Mailgun Setup

### 1. Sign up for Mailgun

- Go to https://www.mailgun.com/
- Create a free account (100 emails/day)

### 2. Add and Verify Domain

- Add your domain in Mailgun dashboard
- Add DNS records (SPF, DKIM, MX)
- Wait for verification

### 3. Get SMTP Credentials

- Go to Sending → Domain settings → SMTP credentials
- Use these values:
  - Host: `smtp.mailgun.org`
  - Port: `587`
  - Username: `postmaster@your-domain.mailgun.org`
  - Password: (from Mailgun dashboard)

### 4. Configure Heroku

```bash
heroku config:set EMAIL_HOST_USER=postmaster@your-domain.mailgun.org
heroku config:set EMAIL_HOST_PASSWORD=your-mailgun-password
```

## Gmail Setup (Local Development)

### 1. Enable 2-Factor Authentication

- Go to Google Account settings
- Enable 2-factor authentication

### 2. Generate App Password

- Go to Security → 2-Step Verification → App passwords
- Create app password for "Mail"
- Copy the 16-character password

### 3. Configure .env

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
DEFAULT_FROM_EMAIL=noreply@tramper.com
```

## Monitoring & Logs

```bash
# View logs
heroku logs --tail

# Monitor performance
heroku ps

# Check database
heroku pg:info

# Check Redis
heroku redis:info
```

## Scaling

```bash
# Scale web dynos
heroku ps:scale web=2

# Scale worker dynos (if using Celery)
heroku ps:scale worker=1
```

## Troubleshooting

### Static Files Not Loading

```bash
heroku run python manage.py collectstatic --noinput
```

### Database Issues

```bash
heroku pg:reset DATABASE_URL
heroku run python manage.py migrate
```

### Email Not Sending

- Check Mailgun dashboard for logs
- Verify DNS records are correct
- Check Heroku config vars: `heroku config`

## Useful Commands

```bash
# Open shell
heroku run python manage.py shell

# Restart app
heroku restart

# View config
heroku config

# Open logs
heroku logs --tail --app tramper-api
```
