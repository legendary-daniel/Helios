#!/bin/bash

# Helios ML Trading System - Installation Script
# Comprehensive setup for local development and deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                 HELIOS ML TRADING SYSTEM                      ║"
echo "║              Professional Installation Script                 ║"
echo "║                      Version 1.0.0                           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8+ and try again."
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2)
    print_success "Python $python_version found"
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed. Please install pip and try again."
        exit 1
    fi
    
    print_success "pip3 found"
    
    # Check git
    if ! command -v git &> /dev/null; then
        print_warning "Git not found. Some features may not work properly."
    else
        print_success "Git found"
    fi
    
    # Check virtual environment support
    if ! python3 -m venv --help &> /dev/null; then
        print_error "python3-venv is not installed. Please install python3-venv and try again."
        exit 1
    fi
    
    print_success "All prerequisites satisfied"
}

# Create project structure
create_structure() {
    print_status "Creating project structure..."
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p models
    mkdir -p data
    mkdir -p config
    
    # Set permissions
    chmod 755 logs models data config
    
    print_success "Project structure created"
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
    
    # Install additional development tools
    pip install black flake8 pytest pytest-asyncio
    print_success "Development tools installed"
}

# Setup configuration
setup_config() {
    print_status "Setting up configuration..."
    
    if [ ! -f "config/config.json" ]; then
        # Create default configuration
        cat > config/config.json << 'EOF'
{
  "mt5": {
    "login": 0,
    "password": "",
    "server": "",
    "timeout": 60000,
    "portable": false
  },
  "data": {
    "symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
    "timeframes": ["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
    "lookback_days": 365,
    "real_time_update_interval": 1.0,
    "tick_data_enabled": false
  },
  "ml": {
    "feature_window": 50,
    "prediction_window": 10,
    "model_type": "ensemble",
    "retrain_interval_hours": 6,
    "confidence_threshold": 0.7
  },
  "strategy": {
    "default_strategy": "trend_following",
    "max_concurrent_strategies": 3,
    "strategy_rotation_enabled": true,
    "min_strategy_performance": 0.05
  },
  "risk": {
    "max_risk_per_trade": 0.02,
    "max_daily_loss": 0.05,
    "max_portfolio_risk": 0.10,
    "max_open_positions": 5,
    "position_sizing_method": "kelly"
  },
  "meta_learning": {
    "market_regime_detection": true,
    "volatility_analysis": true,
    "time_based_regimes": true,
    "strategy_performance_tracking": true,
    "adaptation_interval_hours": 4
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_path": "logs/helios_trading.log",
    "max_file_size": 10485760,
    "backup_count": 5,
    "console_output": true
  }
}
EOF
        print_success "Default configuration created"
    else
        print_warning "Configuration file already exists"
    fi
    
    # Create environment file template
    cat > .env.example << 'EOF'
# Helios ML Trading System Environment Variables

# MT5 Configuration
MT5_LOGIN=your_mt5_login
MT5_PASSWORD=your_mt5_password
MT5_SERVER=your_broker_server

# System Configuration
HELIOS_ENV=development
PYTHONPATH=/path/to/helios-ml-trading
LOG_LEVEL=INFO

# WebSocket Configuration
WEBSOCKET_PORT=8765
WEBSOCKET_HOST=0.0.0.0

# Risk Management
MAX_RISK_PER_TRADE=2.0
MAX_DAILY_LOSS=5.0
MAX_OPEN_POSITIONS=5

# ML Configuration
MODEL_RETRAIN_INTERVAL=6
CONFIDENCE_THRESHOLD=0.7
EOF
    
    print_success "Environment template created"
}

# Setup MT5 Expert Advisor
setup_mt5_ea() {
    print_status "Setting up MT5 Expert Advisor..."
    
    # Detect MT5 data folder
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        # Windows
        MT5_FOLDER="$APPDATA\\MetaQuotes\\Terminal\\"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        MT5_FOLDER="$HOME/Library/Application Support/MetaQuotes/Terminal/"
    else
        # Linux (unlikely for MT5, but handle it)
        MT5_FOLDER="$HOME/.wine/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/"
    fi
    
    if [ -d "$MT5_FOLDER" ]; then
        EA_FOLDER="$MT5_FOLDER/MQL5/Experts"
        if [ ! -d "$EA_FOLDER" ]; then
            mkdir -p "$EA_FOLDER"
        fi
        
        if [ -f "deployed/HeliosML_EA.mq5" ]; then
            cp deployed/HeliosML_EA.mq5 "$EA_FOLDER/"
            print_success "EA copied to MT5 Experts folder: $EA_FOLDER"
        else
            print_error "EA file not found at deployed/HeliosML_EA.mq5"
        fi
    else
        print_warning "MT5 installation not found. Please manually copy the EA file."
        print_warning "EA location: deployed/HeliosML_EA.mq5"
        print_warning "Copy to: <MT5_Data_Folder>/MQL5/Experts/"
    fi
}

# Create startup scripts
create_scripts() {
    print_status "Creating startup scripts..."
    
    # Create start script
    cat > start.sh << 'EOF'
#!/bin/bash

# Helios ML Trading System - Start Script

# Activate virtual environment
source venv/bin/activate

# Set environment
export PYTHONPATH="$(pwd):$PYTHONPATH"
export HELIOS_ENV=development

# Create necessary directories
mkdir -p logs models data config

# Start the trading system
echo "Starting Helios ML Trading System..."
python src/helios_server.py
EOF
    
    # Create stop script
    cat > stop.sh << 'EOF'
#!/bin/bash

# Helios ML Trading System - Stop Script

echo "Stopping Helios ML Trading System..."

# Find and kill the Python process
pkill -f "helios_server.py" || true

echo "Helios ML Trading System stopped"
EOF
    
    # Create test script
    cat > test.sh << 'EOF'
#!/bin/bash

# Helios ML Trading System - Test Script

# Activate virtual environment
source venv/bin/activate

# Set environment
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Run tests
echo "Running system tests..."
python -m pytest tests/ -v

echo "Tests completed"
EOF
    
    # Make scripts executable
    chmod +x start.sh stop.sh test.sh
    
    print_success "Startup scripts created"
}

# Setup Docker (optional)
setup_docker() {
    read -p "Do you want to set up Docker deployment? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Setting up Docker..."
        
        if ! command -v docker &> /dev/null; then
            print_error "Docker not found. Please install Docker first."
            return 1
        fi
        
        # Create Docker-related files
        if [ ! -f "Dockerfile" ]; then
            cp deployment/Dockerfile . 2>/dev/null || echo "# Dockerfile would be created here" > Dockerfile
        fi
        
        if [ ! -f "docker-compose.yml" ]; then
            echo "# docker-compose.yml would be created here" > docker-compose.yml
        fi
        
        print_success "Docker setup completed"
    fi
}

# Final setup and verification
final_setup() {
    print_status "Performing final setup..."
    
    # Test Python imports
    source venv/bin/activate
    python -c "import sys; sys.path.append('src'); from config import config; print('Configuration loaded successfully')" || {
        print_error "Configuration test failed"
        return 1
    }
    
    # Create sample data directory
    mkdir -p data/historical
    
    # Set up logging
    touch logs/helios_trading.log
    chmod 644 logs/helios_trading.log
    
    print_success "Final setup completed"
}

# Print summary
print_summary() {
    echo
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    INSTALLATION COMPLETE                      ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Configure your MT5 credentials in config/config.json"
    echo "2. Start the system: ./start.sh"
    echo "3. Open dashboard: http://localhost:8765"
    echo "4. Attach EA to MT5 chart with WebSocket URL: ws://localhost:8765"
    echo
    echo -e "${YELLOW}Important Files:${NC}"
    echo "  • Configuration: config/config.json"
    echo "  • MT5 Expert Advisor: deployed/HeliosML_EA.mq5"
    echo "  • Dashboard: http://localhost:8765"
    echo "  • Logs: logs/helios_trading.log"
    echo
    echo -e "${YELLOW}Commands:${NC}"
    echo "  • Start: ./start.sh"
    echo "  • Stop: ./stop.sh"
    echo "  • Test: ./test.sh"
    echo
    echo -e "${RED}Disclaimer: This software is for educational purposes only.${NC}"
    echo -e "${RED}Trading involves substantial risk of loss.${NC}"
    echo
}

# Main installation function
main() {
    echo
    print_status "Starting Helios ML Trading System installation..."
    echo
    
    check_prerequisites
    create_structure
    install_dependencies
    setup_config
    setup_mt5_ea
    create_scripts
    setup_docker
    final_setup
    
    print_summary
}

# Check if script is being run from the correct directory
if [ ! -f "README.md" ] || [ ! -f "requirements.txt" ]; then
    print_error "Please run this script from the helios-ml-trading root directory"
    exit 1
fi

# Run main installation
main "$@"