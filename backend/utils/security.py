"""
Production Monitoring, Security & Final Configuration
Complete production-ready setup with monitoring, logging, and security
"""

# security.py - Security middleware and authentication
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os
from ..database import db

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_coach(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated coach"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        coach_id: str = payload.get("sub")
        if coach_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Verify coach exists in database
    async with db.pool.acquire() as conn:
        coach = await conn.fetchrow("SELECT * FROM coaches WHERE id = $1 AND is_active = true", coach_id)
        if coach is None:
            raise credentials_exception
    
    return dict(coach)

# Add to main FastAPI app
# @app.post("/auth/token")
async def login_with_barcode(barcode_data: dict):
    """Authenticate coach with barcode"""
    try:
        barcode = barcode_data.get("barcode")
        
        async with db.pool.acquire() as conn:
            coach = await conn.fetchrow(
                "SELECT * FROM coaches WHERE registration_barcode = $1 AND is_active = true",
                barcode
            )
            
            if not coach:
                raise HTTPException(status_code=401, detail="Invalid barcode")
            
            # Update last login
            await conn.execute(
                "UPDATE coaches SET last_login = $1 WHERE id = $2",
                datetime.now(), coach['id']
            )
            
            # Create access token
            access_token_expires = timedelta(days=5)  # 5-day session as requested
            access_token = create_access_token(
                data={"sub": str(coach['id'])}, expires_delta=access_token_expires
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "coach_data": {
                    "id": str(coach['id']),
                    "name": coach['name'],
                    "email": coach['email'],
                    "timezone": coach['timezone']
                }
            }
    
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

# logging_config.py - Production logging configuration
import logging.config
import os

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s"
        },
        "json": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": "/app/logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": "/app/logs/errors.log",
            "maxBytes": 10485760,
            "backupCount": 5
        },
        "webhook_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "/app/logs/webhooks.log",
            "maxBytes": 10485760,
            "backupCount": 10
        }
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        },
        "webhook": {
            "handlers": ["webhook_file", "console"],
            "level": "INFO",
            "propagate": False
        },
        "error": {
            "handlers": ["error_file", "console"],
            "level": "ERROR",
            "propagate": False
        },
        "uvicorn": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False
        }
    }
}

def setup_logging():
    """Setup production logging"""
    # Create logs directory
    os.makedirs("/app/logs", exist_ok=True)
    
    # Configure logging
    logging.config.dictConfig(LOGGING_CONFIG)
    
    # Test logging
    logger = logging.getLogger(__name__)
    logger.info("Logging configuration loaded successfully")

# rate_limiting.py - Advanced rate limiting
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis.asyncio as aioredis

# Create limiter
limiter = Limiter(key_func=get_remote_address)

# Rate limiting configurations
RATE_LIMITS = {
    "default": "100/minute",
    "webhook": "1000/minute",
    "auth": "10/minute",
    "export": "5/minute",
    "voice_processing": "20/minute"
}

# Add to main app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply rate limits to endpoints
@app.post("/register",
          summary="Register Coach (Rate Limited)",
          description="""
          Register a new coach with rate limiting applied.
          
          This is a rate-limited version of the coach registration endpoint
          to prevent abuse and ensure system stability.
          
          **Features:**
          - Rate limiting protection
          - Coach registration
          - Input validation
          - Abuse prevention
          - System stability
          
          **Use Cases:**
          - Coach registration
          - Rate-limited access
          - System protection
          - Abuse prevention
          """,
          tags=["Coach Management"],
          responses={
              200: {"description": "Coach registered successfully"},
              400: {"description": "Invalid registration data"},
              429: {"description": "Rate limit exceeded"},
              500: {"description": "Registration error"}
          })
@limiter.limit(RATE_LIMITS["auth"])
async def register_coach_with_limit(request: Request, registration: CoachRegistration):
    return await register_coach(registration)

@app.post("/webhook/whatsapp",
          summary="WhatsApp Webhook (Rate Limited)",
          description="""
          Handle WhatsApp webhook events with rate limiting applied.
          
          This is a rate-limited version of the WhatsApp webhook endpoint
          to prevent abuse and ensure system stability.
          
          **Features:**
          - Rate limiting protection
          - Webhook event handling
          - Message processing
          - Abuse prevention
          - System stability
          
          **Use Cases:**
          - Webhook processing
          - Rate-limited access
          - System protection
          - Abuse prevention
          """,
          tags=["WhatsApp Webhooks"],
          responses={
              200: {"description": "Webhook processed successfully"},
              400: {"description": "Invalid webhook data"},
              429: {"description": "Rate limit exceeded"},
              500: {"description": "Processing error"}
          })
@limiter.limit(RATE_LIMITS["webhook"])
async def whatsapp_webhook_with_limit(request: Request):
    return await handle_whatsapp_webhook(request)

# backup.py - Database backup and restore
import subprocess
import boto3
from datetime import datetime
import gzip
import os

class DatabaseBackup:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.bucket_name = os.getenv('BACKUP_S3_BUCKET', 'coaching-system-backups')
    
    def create_backup(self):
        """Create database backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"coaching_system_backup_{timestamp}.sql"
            backup_path = f"/backup/{backup_filename}"
            
            # Create PostgreSQL dump
            dump_command = [
                "pg_dump",
                "-h", os.getenv("DB_HOST"),
                "-U", os.getenv("DB_USER"),
                "-d", os.getenv("DB_NAME"),
                "-f", backup_path,
                "--verbose"
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = os.getenv("DB_PASSWORD")
            
            result = subprocess.run(dump_command, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Backup failed: {result.stderr}")
            
            # Compress backup
            compressed_path = f"{backup_path}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Upload to S3
            s3_key = f"daily/{backup_filename}.gz"
            self.s3_client.upload_file(compressed_path, self.bucket_name, s3_key)
            
            # Clean up local files
            os.remove(backup_path)
            os.remove(compressed_path)
            
            logger.info(f"Backup created successfully: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Backup creation error: {e}")
            raise

    def restore_backup(self, backup_key: str):
        """Restore database from backup"""
        try:
            # Download from S3
            local_path = f"/backup/restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql.gz"
            self.s3_client.download_file(self.bucket_name, backup_key, local_path)
            
            # Decompress
            sql_path = local_path.replace('.gz', '')
            with gzip.open(local_path, 'rb') as f_in:
                with open(sql_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Restore to database
            restore_command = [
                "psql",
                "-h", os.getenv("DB_HOST"),
                "-U", os.getenv("DB_USER"),
                "-d", os.getenv("DB_NAME"),
                "-f", sql_path
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = os.getenv("DB_PASSWORD")
            
            result = subprocess.run(restore_command, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Restore failed: {result.stderr}")
            
            # Clean up
            os.remove(local_path)
            os.remove(sql_path)
            
            logger.info(f"Database restored successfully from: {backup_key}")
            
        except Exception as e:
            logger.error(f"Restore error: {e}")
            raise

# Add backup endpoints to main app
backup_service = DatabaseBackup()

@app.post("/admin/backup",
          summary="Create Database Backup",
          description="""
          Create a database backup for administrative purposes.
          
          This endpoint allows administrators to create database backups
          for data protection and disaster recovery purposes.
          
          **Features:**
          - Database backup creation
          - Data protection
          - Disaster recovery
          - Administrative access
          - Backup management
          
          **Use Cases:**
          - Data protection
          - Disaster recovery
          - System maintenance
          - Administrative tasks
          """,
          tags=["Admin - System Management"],
          responses={
              200: {"description": "Backup created successfully"},
              401: {"description": "Unauthorized access"},
              500: {"description": "Backup error"}
          })
async def create_backup(current_coach: dict = Depends(get_current_coach)):
    """Create database backup (admin only)"""
    # Add admin role check here
    try:
        backup_key = backup_service.create_backup()
        return {"status": "success", "backup_key": backup_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

# health_monitoring.py - Advanced health monitoring
import psutil
import asyncpg
from datetime import datetime

@app.get("/health/detailed",
         summary="Detailed Health Check",
         description="""
         Comprehensive health check for system monitoring.
         
         This endpoint provides detailed system health information including
         resource usage, performance metrics, and component status.
         
         **Features:**
         - Comprehensive health data
         - Resource monitoring
         - Performance metrics
         - Component status
         - System diagnostics
         
         **Use Cases:**
         - System monitoring
         - Health diagnostics
         - Performance analysis
         - Troubleshooting
         """,
         tags=["System Health"],
         responses={
             200: {"description": "Detailed health data retrieved successfully"},
             500: {"description": "Health check error"}
         })
async def detailed_health_check():
    """Comprehensive health check for monitoring"""
    health_data = {
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "components": {}
    }
    
    try:
        # Database health
        async with db.pool.acquire() as conn:
            db_version = await conn.fetchval("SELECT version()")
            active_connections = await conn.fetchval(
                "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            
            health_data["components"]["database"] = {
                "status": "healthy",
                "version": db_version.split()[1],
                "active_connections": active_connections
            }
    except Exception as e:
        health_data["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_data["status"] = "degraded"
    
    # Redis health
    try:
        redis_client = aioredis.from_url(os.getenv("REDIS_URL"))
        await redis_client.ping()
        info = await redis_client.info()
        
        health_data["components"]["redis"] = {
            "status": "healthy",
            "version": info.get("redis_version"),
            "memory_usage": info.get("used_memory_human")
        }
        await redis_client.close()
    except Exception as e:
        health_data["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_data["status"] = "degraded"
    
    # OpenAI API health
    try:
        openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Simple test request
        await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )
        
        health_data["components"]["openai"] = {"status": "healthy"}
    except Exception as e:
        health_data["components"]["openai"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_data["status"] = "degraded"
    
    # System resources
    health_data["components"]["system"] = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent
    }
    
    # Check if any critical component is down
    critical_components = ["database", "redis"]
    for component in critical_components:
        if health_data["components"].get(component, {}).get("status") == "unhealthy":
            health_data["status"] = "unhealthy"
            break
    
    return health_data

# alerting.py - Alert system
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class AlertManager:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.alert_email = os.getenv("ALERT_EMAIL")
    
    async def send_alert(self, subject: str, message: str, severity: str = "warning"):
        """Send alert email"""
        try:
            if not all([self.smtp_username, self.smtp_password, self.alert_email]):
                logger.warning("Email alerts not configured")
                return
            
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = self.alert_email
            msg['Subject'] = f"[{severity.upper()}] Coaching System: {subject}"
            
            body = f"""
Coaching System Alert

Severity: {severity.upper()}
Time: {datetime.now().isoformat()}
Subject: {subject}

Details:
{message}

---
This is an automated alert from the Coaching System monitoring.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.smtp_username, self.alert_email, text)
            server.quit()
            
            logger.info(f"Alert sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

alert_manager = AlertManager()

# Middleware for request monitoring
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    """Monitor API requests and response times"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.observe(duration)
    
    # Alert on slow requests (>10 seconds)
    if duration > 10:
        await alert_manager.send_alert(
            "Slow API Request",
            f"Request to {request.url.path} took {duration:.2f} seconds",
            "warning"
        )
    
    # Alert on errors
    if response.status_code >= 500:
        await alert_manager.send_alert(
            "API Error",
            f"Error {response.status_code} on {request.method} {request.url.path}",
            "error"
        )
    
    return response

# deployment_script.py - Automated deployment
#!/usr/bin/env python3

import subprocess
import sys
import os
import time

def run_command(command, description):
    """Run shell command with error handling"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        sys.exit(1)

def deploy_production():
    """Deploy coaching system to production"""
    print("🚀 Starting production deployment...")
    
    # Pre-deployment checks
    print("\n📋 Pre-deployment checks...")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found. Please create it from .env.production template")
        sys.exit(1)
    
    # Check required environment variables
    required_vars = [
        'DB_PASSWORD', 'OPENAI_API_KEY', 'GOOGLE_CLIENT_ID', 
        'META_APP_ID', 'WEBHOOK_VERIFY_TOKEN'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    print("✅ Environment variables check passed")
    
    # Docker checks
    run_command("docker --version", "Checking Docker installation")
    run_command("docker-compose --version", "Checking Docker Compose installation")
    
    # Build and deploy
    print("\n🏗️ Building and deploying services...")
    
    # Stop existing services
    run_command("docker-compose -f docker-compose.prod.yml down", "Stopping existing services")
    
    # Pull latest images
    run_command("docker-compose -f docker-compose.prod.yml pull", "Pulling latest images")
    
    # Build and start services
    run_command("docker-compose -f docker-compose.prod.yml up --build -d", "Building and starting services")
    
    # Wait for services to be ready
    print("\n⏳ Waiting for services to start...")
    time.sleep(30)
    
    # Health checks
    print("\n🔍 Running health checks...")
    
    max_retries = 10
    for i in range(max_retries):
        try:
            result = subprocess.run(
                "curl -f http://localhost:8000/health",
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                print("✅ Backend health check passed")
                break
        except:
            pass
        
        if i == max_retries - 1:
            print("❌ Backend health check failed")
            sys.exit(1)
        
        print(f"⏳ Retrying health check ({i+1}/{max_retries})...")
        time.sleep(10)
    
    # Database migration check
    run_command(
        "docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d coaching_system -c 'SELECT COUNT(*) FROM coaches;'",
        "Checking database schema"
    )
    
    # Show running services
    print("\n📊 Service status:")
    run_command("docker-compose -f docker-compose.prod.yml ps", "Checking service status")
    
    print("\n🎉 Deployment completed successfully!")
    print("\n📋 Access your system:")
    print("   🌐 Frontend: https://your-domain.com")
    print("   🔧 API: https://your-domain.com/api/health")
    print("   📊 Monitoring: http://your-domain.com:3001")
    print("   📈 Metrics: http://your-domain.com:9090")
    
    print("\n🔧 Next steps:")
    print("1. Configure your domain DNS to point to this server")
    print("2. Update SSL certificates in ./ssl/ directory")
    print("3. Set up WhatsApp Business API webhook: https://your-domain.com/webhook/whatsapp")
    print("4. Test barcode registration with a real coach")
    print("5. Monitor logs: docker-compose -f docker-compose.prod.yml logs -f")

if __name__ == "__main__":
    deploy_production()