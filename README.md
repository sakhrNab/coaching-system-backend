# Coaching System Backend

A comprehensive AI-powered coaching platform built with FastAPI, featuring WhatsApp Business API integration, OpenAI AI responses, and complete Docker containerization.

## 🚀 Features

- **FastAPI Backend**: High-performance async API with automatic documentation
- **WhatsApp Business API**: Complete integration for messaging and webhooks
- **OpenAI Integration**: AI-powered coaching responses and analysis
- **Google OAuth**: Secure authentication and contacts import
- **PostgreSQL Database**: Robust data storage with complete schema
- **JWT Authentication**: Secure token-based authentication
- **Docker Ready**: Full containerization with docker-compose
- **Comprehensive Testing**: Extensive test suite for all endpoints
- **Production Ready**: Security best practices and monitoring

## 🛠️ Quick Start

### Prerequisites
- Docker Desktop installed and running
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/sakhrNab/coaching-system-backend.git
   cd coaching-system-backend
   ```

2. **Create environment file**
   ```bash
   # Copy and configure your environment variables
   cp .env.example .env
   ```

3. **Start the application**
   ```bash
   docker-compose up --build -d
   ```

4. **Test the API**
   ```bash
   # Check health endpoint
   curl http://localhost:8001/health

   # View API documentation
   open http://localhost:8001/docs
   ```

## 📋 API Endpoints

### Core Features
- `POST /register` - Coach registration
- `GET /coaches/{id}/categories` - Get coaching categories
- `POST /coaches/{id}/clients` - Add new clients
- `POST /coaches/{id}/send-message` - Send messages
- `POST /webhook/whatsapp` - WhatsApp webhooks

### Authentication
- `POST /auth/token` - JWT token generation
- `GET /auth/me` - Get current user info

### Administration
- `GET /admin/stats` - System statistics
- `POST /admin/reset-token` - Reset API tokens

## 🐳 Docker Deployment

### Production Setup
```bash
# Build and run in production mode
docker-compose -f docker-compose.yml up --build -d
```

### Coolify Deployment
See [COOLIFY_DEPLOYMENT.md](./COOLIFY_DEPLOYMENT.md) for complete Coolify deployment guide.

## 🧪 Testing

### Run All Tests
```bash
# Run comprehensive endpoint tests
docker exec coaching_backend_prod python -c "import asyncio; from backend.tests.test_all_endpoints import test_all_endpoints; asyncio.run(test_all_endpoints())"
```

### Database Tests
```bash
# Test database connectivity
docker exec coaching_backend_prod python backend/tests/test_db.py
```

## 📊 Database Schema

The system uses PostgreSQL with the following main tables:
- `coaches` - Coach registration and API tokens
- `clients` - Client information and categories
- `goals` - Client goals and progress tracking
- `message_templates` - Customizable message templates
- `message_history` - Complete messaging history

## 🔒 Security

- **Environment Variables**: All secrets stored in environment variables
- **JWT Tokens**: Secure authentication with configurable expiration
- **Input Validation**: Comprehensive input validation and sanitization
- **Rate Limiting**: Built-in rate limiting for API endpoints
- **HTTPS**: Production deployments use HTTPS

## 📁 Project Structure

```
coaching-system-backend/
├── backend/                 # Main application code
│   ├── main.py             # FastAPI application entry point
│   ├── core_api.py         # Core API endpoints
│   ├── admin_api.py        # Admin endpoints
│   ├── webhook_handler.py  # WhatsApp webhook handling
│   ├── database.py         # Database connection and utilities
│   ├── utils/              # Utility modules
│   └── tests/              # Comprehensive test suite
├── database/               # Database schema and migrations
├── infrastructure/         # Docker and deployment files
├── Scripts/                # Migration and utility scripts
├── docker-compose.yml      # Docker orchestration
├── requirements.txt        # Python dependencies
└── .gitignore             # Git ignore rules
```

## 🚀 Deployment Options

### Local Development
```bash
docker-compose up --build -d
```

### Coolify (Recommended)
1. Push code to GitHub
2. Connect Coolify to your repository
3. Configure environment variables
4. Deploy with automatic SSL

### Manual Server Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DB_PASSWORD=your_password
export OPENAI_API_KEY=your_key
# ... other variables

# Run the application
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 📚 Documentation

- **API Documentation**: Available at `/docs` when running locally
- **Setup Guide**: See [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- **Coolify Deployment**: See [COOLIFY_DEPLOYMENT.md](./COOLIFY_DEPLOYMENT.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter issues:
1. Check the setup guide for common problems
2. Review the troubleshooting section
3. Check the API documentation
4. Open an issue on GitHub

---

**Happy Coaching! 🎯**
