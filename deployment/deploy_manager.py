"""
Helios ML Trading System - Deployment Manager
Handles deployment and configuration for free server environments
"""

import os
import sys
import json
import yaml
import docker
import subprocess
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import shutil
import tarfile
import tempfile

class HeliosDeploymentManager:
    """Deployment manager for Helios ML Trading System"""
    
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.project_root = Path(__file__).parent.parent
        
        # Free server configurations
        self.free_servers = {
            'render': {
                'name': 'Render',
                'type': 'web_service',
                'plan': 'free',
                'runtime': 'python',
                'build_command': 'pip install -r requirements.txt',
                'start_command': 'python src/helios_server.py'
            },
            'railway': {
                'name': 'Railway',
                'type': 'railway_app',
                'plan': 'free',
                'runtime': 'python',
                'build_command': 'pip install -r requirements.txt',
                'start_command': 'python src/helios_server.py'
            },
            'pythonanywhere': {
                'name': 'PythonAnywhere',
                'type': 'web_app',
                'plan': 'free',
                'runtime': 'python',
                'setup_instructions': [
                    '1. Upload project files',
                    '2. Create virtual environment',
                    '3. Install requirements',
                    '4. Configure web app'
                ]
            },
            'heroku': {
                'name': 'Heroku',
                'type': 'heroku_app',
                'plan': 'free',
                'runtime': 'python',
                'build_command': 'pip install -r requirements.txt',
                'start_command': 'python src/helios_server.py'
            },
            'vercel': {
                'name': 'Vercel',
                'type': 'serverless',
                'plan': 'free',
                'runtime': 'python',
                'build_command': 'pip install -r requirements.txt',
                'start_command': 'python src/helios_server.py'
            }
        }
    
    def generate_dockerfile(self, target_server: str = 'render') -> str:
        """Generate Dockerfile for containerized deployment"""
        
        dockerfile_content = f"""# Helios ML Trading System Docker Configuration
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    libhdf5-dev \\
    libatlas-base-dev \\
    gfortran \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs models data config deployed

# Set environment variables
ENV PYTHONPATH=/app
ENV HELIOS_ENV=production

# Expose port for WebSocket server
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8765/health || exit 1

# Start command
CMD ["python", "src/helios_server.py"]
"""
        
        return dockerfile_content
    
    def generate_docker_compose(self) -> str:
        """Generate docker-compose.yml for local development"""
        
        compose_content = """version: '3.8'

services:
  helios-ml-trading:
    build: .
    ports:
      - "8765:8765"
      - "5000:5000"
    environment:
      - HELIOS_ENV=development
      - PYTHONPATH=/app
    volumes:
      - ./logs:/app/logs
      - ./models:/app/models
      - ./data:/app/data
      - ./config:/app/config
    restart: unless-stopped
    networks:
      - helios-network

  # Optional: Add Redis for caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
    networks:
      - helios-network

  # Optional: Add PostgreSQL for data persistence
  postgres:
    image: postgres:13-alpine
    environment:
      - POSTGRES_DB=helios_trading
      - POSTGRES_USER=helios
      - POSTGRES_PASSWORD=helios_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - helios-network

networks:
  helios-network:
    driver: bridge

volumes:
  postgres_data:
"""
        
        return compose_content
    
    def generate_render_config(self) -> Dict[str, Any]:
        """Generate Render.com deployment configuration"""
        
        return {
            'services': [
                {
                    'type': 'web',
                    'name': 'helios-ml-trading-system',
                    'env': 'python',
                    'buildCommand': 'pip install -r requirements.txt',
                    'startCommand': 'python src/helios_server.py',
                    'plan': 'free',
                    'regions': ['oregon'],
                    'envVars': [
                        {
                            'key': 'HELIOS_ENV',
                            'value': 'production'
                        },
                        {
                            'key': 'PYTHONPATH',
                            'value': '/opt/render/project/src'
                        }
                    ],
                    'scaling': {
                        'minInstances': 0,
                        'maxInstances': 1,
                        'targetCpuPercent': 50
                    }
                }
            ]
        }
    
    def generate_railway_config(self) -> Dict[str, Any]:
        """Generate Railway.app deployment configuration"""
        
        return {
            'build': {
                'builder': 'nixpacks'
            },
            'deploy': {
                'startCommand': 'python src/helios_server.py',
                'healthcheckPath': '/health',
                'healthcheckTimeout': 300,
                'restartPolicyType': 'on_failure',
                'restartPolicyMaxRetries': 10
            },
            'environments': {
                'production': {
                    'variables': {
                        'HELIOS_ENV': 'production',
                        'PYTHONPATH': '/app'
                    }
                }
            }
        }
    
    def generate_heroku_config(self) -> Dict[str, Any]:
        """Generate Heroku deployment configuration"""
        
        return {
            'stack': 'heroku-20',
            'buildpacks': [
                {
                    'url': 'heroku/python'
                }
            ],
            'env': {
                'HELIOS_ENV': 'production',
                'PYTHONPATH': '/app'
            },
            'formation': {
                'web': {
                    'quantity': 0,
                    'size': 'eco'
                }
            }
        }
    
    def generate_vercel_config(self) -> Dict[str, Any]:
        """Generate Vercel deployment configuration"""
        
        return {
            'version': 2,
            'builds': [
                {
                    'src': 'src/helios_server.py',
                    'use': '@vercel/python'
                }
            ],
            'routes': [
                {
                    'src': '/(.*)',
                    'dest': 'src/helios_server.py'
                }
            ],
            'env': {
                'HELIOS_ENV': 'production',
                'PYTHONPATH': '/app'
            },
            'functions': {
                'src/helios_server.py': {
                    'runtime': 'python3.9',
                    'memory': 1024,
                    'maxDuration': 300
                }
            }
        }
    
    def create_deployment_package(self, target_server: str) -> str:
        """Create deployment package for target server"""
        
        package_dir = Path(tempfile.mkdtemp())
        
        try:
            # Copy project files
            shutil.copytree(self.project_root, package_dir / 'helios-ml-trading', 
                          ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git', '.venv'))
            
            # Generate server-specific files
            if target_server == 'render':
                # Render deployment
                render_config = self.generate_render_config()
                with open(package_dir / 'render.yaml', 'w') as f:
                    yaml.dump(render_config, f)
                    
                # Dockerfile for Render
                dockerfile = self.generate_dockerfile(target_server)
                with open(package_dir / 'Dockerfile', 'w') as f:
                    f.write(dockerfile)
                    
            elif target_server == 'railway':
                # Railway deployment
                railway_config = self.generate_railway_config()
                with open(package_dir / 'railway.json', 'w') as f:
                    json.dump(railway_config, f, indent=2)
                    
                # Dockerfile for Railway
                dockerfile = self.generate_dockerfile(target_server)
                with open(package_dir / 'Dockerfile', 'w') as f:
                    f.write(dockerfile)
                    
            elif target_server == 'heroku':
                # Heroku deployment
                heroku_config = self.generate_heroku_config()
                with open(package_dir / 'app.json', 'w') as f:
                    json.dump(heroku_config, f, indent=2)
                    
                # Procfile for Heroku
                with open(package_dir / 'Procfile', 'w') as f:
                    f.write('web: python src/helios_server.py\n')
                    
            # Add deployment documentation
            self.create_deployment_readme(target_server, package_dir)
            
            # Create tarball
            package_path = package_dir / f'helios-ml-trading-{target_server}.tar.gz'
            with tarfile.open(package_path, 'w:gz') as tar:
                tar.add(package_dir / 'helios-ml-trading', arcname='helios-ml-trading')
            
            return str(package_path)
            
        except Exception as e:
            self.logger.error(f"Error creating deployment package: {e}")
            # Cleanup on error
            shutil.rmtree(package_dir, ignore_errors=True)
            raise
    
    def create_deployment_readme(self, target_server: str, package_dir: Path):
        """Create deployment instructions for target server"""
        
        server_info = self.free_servers.get(target_server, {})
        server_name = server_info.get('name', target_server.title())
        
        readme_content = f"""# Helios ML Trading System - {server_name} Deployment

## Deployment Instructions

### Quick Start

1. **Upload Files**: Upload the entire 'helios-ml-trading' folder to {server_name}
2. **Configure Environment**: Set up the required environment variables
3. **Install Dependencies**: Run the installation command
4. **Start Application**: Launch the trading system

### Detailed Steps

{self._get_detailed_instructions(target_server)}

### Environment Variables

Set the following environment variables:

```bash
HELIOS_ENV=production
PYTHONPATH=/path/to/app
MT5_LOGIN=your_mt5_login
MT5_PASSWORD=your_mt5_password
MT5_SERVER=your_broker_server
```

### Monitoring and Logs

- Monitor application logs at: `logs/helios_trading.log`
- WebSocket server runs on port 8765
- Health check endpoint: `/health`

### Troubleshooting

Common issues and solutions:

1. **WebSocket Connection Failed**: Ensure MT5 is running and EA is attached
2. **Insufficient Memory**: Consider upgrading to a paid plan
3. **Model Loading Errors**: Check models directory permissions
4. **Trading Permissions**: Verify MT5 account has trading enabled

### Performance Optimization

- Use Redis for caching (optional)
- Enable model caching to reduce load times
- Monitor CPU and memory usage
- Consider upgrading for better performance

### Support

For issues and support, please check:
- Application logs
- System resource usage
- Network connectivity
- MT5 terminal status

---
Helios ML Trading System v1.0
Copyright 2025, MiniMax Agent
"""
        
        readme_path = package_dir / 'DEPLOYMENT.md'
        with open(readme_path, 'w') as f:
            f.write(readme_content)
    
    def _get_detailed_instructions(self, target_server: str) -> str:
        """Get detailed deployment instructions for specific server"""
        
        instructions = {
            'render': """
#### Render.com Deployment

1. **Create Account**: Sign up at render.com
2. **New Service**: Click "New" → "Web Service"
3. **Connect Repository**: Upload the deployment package or connect GitHub
4. **Configure Service**:
   - Name: helios-ml-trading-system
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python src/helios_server.py`
5. **Environment**: Set to Free tier
6. **Deploy**: Click "Create Web Service"

#### Configuration:
- Free tier limitations: 750 hours/month, 1GB RAM
- Auto-sleep after 15 minutes of inactivity
- Perfect for development and testing

#### Notes:
- Use environment variables for sensitive data
- Monitor usage to avoid hitting limits
- Consider upgrading for continuous operation
""",
            
            'railway': """
#### Railway.app Deployment

1. **Create Account**: Sign up at railway.app
2. **New Project**: Click "New Project" → "Deploy from GitHub repo" or upload
3. **Configure**: Railway will auto-detect Python and install dependencies
4. **Environment**: Free tier provides $5 credit monthly
5. **Deploy**: Automatic deployment on code changes

#### Configuration:
- $5 free credit per month
- 500 execution hours
- 1GB RAM, 1GB storage
- No cold starts

#### Notes:
- More generous than Render
- Good performance for trading applications
- Easy setup and deployment
""",
            
            'heroku': """
#### Heroku Deployment

1. **Create Account**: Sign up at heroku.com
2. **Install Heroku CLI**: Download and install Heroku Command Line
3. **Login**: `heroku login`
4. **Create App**: `heroku create helios-ml-trading`
5. **Deploy**: 
   ```bash
   git init
   git add .
   git commit -m "Initial deploy"
   git push heroku main
   ```

#### Configuration:
- Free tier discontinued, use Hobby dyno ($7/month)
- 1GB RAM, 1GB storage
- Good for production use

#### Notes:
- Most mature platform
- Reliable and well-documented
- Requires paid plan for continuous operation
""",
            
            'vercel': """
#### Vercel Deployment

1. **Create Account**: Sign up at vercel.com
2. **Import Project**: Click "Import Project" and upload the package
3. **Configure**: Vercel auto-detects Python settings
4. **Deploy**: Automatic deployment
5. **Domain**: Get a free vercel.app subdomain

#### Configuration:
- Free tier: 100GB bandwidth, 10GB storage
- Serverless functions (300s timeout)
- Edge network distribution

#### Notes:
- Great for APIs and serverless apps
- Consider function timeout limits for long-running processes
- Excellent performance and reliability
""",
            
            'pythonanywhere': """
#### PythonAnywhere Deployment

1. **Create Account**: Sign up at pythonanywhere.com
2. **Upload Files**: Upload the deployment package via web interface
3. **Bash Console**: Open a Bash console
4. **Install Dependencies**:
   ```bash
   pip3.10 install --user -r requirements.txt
   ```
5. **Web App**: Create a new web app with manual configuration
6. **Configure**: Point to helios_server.py

#### Configuration:
- Free tier: 1 CPU core, 512MB RAM
- Limited execution time per session
- Suitable for development and testing

#### Notes:
- Beginner-friendly
- All Python, no Node.js or other runtimes
- Good for learning and experimentation
"""
        }
        
        return instructions.get(target_server, "Instructions not available for this platform.")
    
    def deploy_to_platform(self, target_server: str, package_path: str) -> bool:
        """Deploy to the specified platform (requires manual steps)"""
        
        try:
            server_info = self.free_servers.get(target_server)
            if not server_info:
                self.logger.error(f"Unknown deployment target: {target_server}")
                return False
            
            self.logger.info(f"Deployment package created for {server_info['name']}")
            self.logger.info(f"Package location: {package_path}")
            self.logger.info(f"Next steps: Upload to {server_info['name']} and follow deployment instructions")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in deployment: {e}")
            return False
    
    def create_local_docker_setup(self):
        """Create local Docker setup for development"""
        
        try:
            # Create Dockerfile
            dockerfile = self.generate_dockerfile('local')
            with open(self.project_root / 'Dockerfile', 'w') as f:
                f.write(dockerfile)
            
            # Create docker-compose.yml
            compose_content = self.generate_docker_compose()
            with open(self.project_root / 'docker-compose.yml', 'w') as f:
                f.write(compose_content)
            
            # Create .dockerignore
            dockerignore_content = """__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis
.pytest_cache
.git
.gitignore
README.md
LICENSE
"""
            with open(self.project_root / '.dockerignore', 'w') as f:
                f.write(dockerignore_content)
            
            self.logger.info("Local Docker setup created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating local Docker setup: {e}")
            return False
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get deployment status and options"""
        
        return {
            'supported_platforms': list(self.free_servers.keys()),
            'recommended_platforms': [
                'railway',  # Most generous free tier
                'render',   # Easy deployment
                'heroku'    # Most mature (paid)
            ],
            'requirements': {
                'python': '3.8+',
                'memory': '1GB minimum',
                'storage': '2GB recommended',
                'network': 'Stable internet for MT5 connection'
            },
            'features': [
                'WebSocket server for MT5 communication',
                'Multi-strategy trading system',
                'Machine learning model integration',
                'Meta-learning for strategy selection',
                'Risk management and position sizing',
                'Real-time market data processing'
            ],
            'limitations': {
                'free_tier': 'Limited execution time and resources',
                'cold_starts': 'Some platforms may have startup delays',
                'network': 'Dependent on platform network stability'
            }
        }

if __name__ == "__main__":
    # Test deployment manager
    logging.basicConfig(level=logging.INFO)
    
    manager = HeliosDeploymentManager()
    
    # Show deployment options
    status = manager.get_deployment_status()
    print("Helios ML Trading System Deployment Options:")
    print(f"Supported platforms: {status['supported_platforms']}")
    print(f"Recommended: {status['recommended_platforms']}")
    
    # Create Docker setup
    if manager.create_local_docker_setup():
        print("Local Docker setup created")
    
    # Generate deployment package for Railway (most recommended)
    try:
        package_path = manager.create_deployment_package('railway')
        print(f"Deployment package created: {package_path}")
    except Exception as e:
        print(f"Error creating package: {e}")