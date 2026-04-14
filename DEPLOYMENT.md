# DEPLOYMENT.md - Production Deployment Guide

## Quick Start with Docker

### Prerequisites
- Docker >= 20.10
- Docker Compose >= 1.29
- 4GB free disk space
- 2GB free RAM

### Setup Steps

1. **Clone the repository:**
```bash
git clone https://github.com/mvson1993-gif/cw-trading-system.git
cd cw-trading-system
```

2. **Configure environment:**
```bash
# Copy production environment template
cp .env.production .env

# Edit .env with your configuration
nano .env
```

3. **Generate encryption key:**
```bash
python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
# Copy the output and add to .env
```

4. **Build and deploy:**
```bash
# Build the Docker image
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

5. **Verify deployment:**
```bash
# Access the application
open http://localhost:8501

# Check database health
docker-compose logs db | grep "ready"

# Test API connectivity
curl http://localhost:8501/_stcore/health
```

### Configuration

#### Database Setup
- PostgreSQL runs on `localhost:5432`
- Default credentials: `trading:trading_password`
- Database: `cw_trading`
- PgAdmin available at `http://localhost:5050`

#### Broker API Setup
1. Configure OCBS credentials in `.env`
2. Set `OCBS_ENABLED=true` to enable trading
3. Set `RECONCILIATION_ENABLED=true` for position reconciliation

#### Email Alerts
1. For Gmail: Use App Passwords (not regular password)
2. Generate app password: https://myaccount.google.com/apppasswords
3. Add to `.env`:
   ```
   EMAIL_ENABLED=true
   EMAIL_FROM=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   ```

#### SMS Alerts
1. Sign up for Twilio: https://www.twilio.com
2. Get your credentials from dashboard
3. Add to `.env`:
   ```
   SMS_ENABLED=true
   TWILIO_ACCOUNT_SID=...
   TWILIO_AUTH_TOKEN=...
   TWILIO_FROM_NUMBER=+...
   ```

### Monitoring

#### View Logs
```bash
# View all services
docker-compose logs -f

# View specific service
docker-compose logs -f app
docker-compose logs -f db
```

#### Health Checks
```bash
# List service status
docker-compose ps

# Check application health
docker exec cw-trading-system curl http://localhost:8501/_stcore/health

# Check database
docker exec cw-trading-db pg_isready -U trading
```

### Maintenance

#### Database Backup
```bash
# Backup database
docker exec cw-trading-db pg_dump -U trading -d cw_trading > backup.sql

# Restore from backup
cat backup.sql | docker exec -i cw-trading-db psql -U trading -d cw_trading
```

#### Update Application
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d --force-recreate
```

#### Clean Up
```bash
# Stop all services
docker-compose down

# Remove volumes (CAUTION: deletes data)
docker-compose down -v

# Clean up images
docker system prune -a
```

### Troubleshooting

#### Container won't start
```bash
# Check logs for errors
docker-compose logs app

# Verify environment configuration
docker-compose config | grep -A 50 "app:"

# Rebuild from scratch
docker-compose build --no-cache && docker-compose up
```

#### Database connection errors
```bash
# Check database is running
docker-compose ps db

# Test connection
docker exec cw-trading-db psql -U trading -d cw_trading -c "SELECT 1;"

# Check network connectivity
docker-compose down && docker-compose up -d
```

#### Port conflicts
```bash
# Change ports in docker-compose.yml
# Or stop conflicting services:
sudo lsof -i :8501
sudo kill -9 <PID>
```

### Production Best Practices

1. **Security:**
   - Use strong encryption keys
   - Rotate credentials regularly
   - Use private networks for database access
   - Enable SSL/TLS for external APIs

2. **Performance:**
   - Adjust DB connection pool sizes based on load
   - Monitor resource usage
   - Use PostgreSQL for production (not SQLite)
   - Implement caching strategies

3. **Backup & Recovery:**
   - Schedule daily database backups
   - Store backups in secure location
   - Test restore procedures regularly
   - Implement disaster recovery plan

4. **Monitoring:**
   - Set up log aggregation (ELK stack)
   - Monitor application metrics
   - Alert on errors and anomalies
   - Track system performance

5. **Updates:**
   - Keep Docker images updated
   - Review security patches
   - Test updates in staging first
   - Plan maintenance windows

### Advanced Configuration

#### Custom Database
To use an external PostgreSQL database:
```bash
# Update DATABASE_URL in .env
DATABASE_URL=postgresql://user:password@external-host:5432/database

# Don't run the database container
docker-compose up -d --scale db=0
```

#### SSL/TLS for Streamlit
Create an nginx reverse proxy in docker-compose.yml for HTTPS support.

#### Kubernetes Deployment
Create a Helm chart for Kubernetes deployment. See `/scripts/k8s/` for examples.

---

**For more information, see:**
- README.md - Project overview
- .env.production - Configuration template
- Requirements.txt - Python dependencies