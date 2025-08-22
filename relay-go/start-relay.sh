#!/bin/bash

# Enhanced Nostr Home Relay Startup Script (Go Implementation)
# This script provides easy startup options for the Go-based relay

set -e

# Configuration
RELAY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$RELAY_DIR/../data"
BINARY_NAME="relay-server"
BINARY_PATH="$RELAY_DIR/$BINARY_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if binary exists
check_binary() {
    if [ ! -f "$BINARY_PATH" ]; then
        log_warning "Relay binary not found at $BINARY_PATH"
        log_info "Building relay binary..."
        
        cd "$RELAY_DIR"
        if ! go build -o "$BINARY_NAME" main.go; then
            log_error "Failed to build relay binary"
            exit 1
        fi
        
        log_success "Relay binary built successfully"
    fi
}

# Create data directory if it doesn't exist
setup_data_dir() {
    if [ ! -d "$DATA_DIR" ]; then
        log_info "Creating data directory: $DATA_DIR"
        mkdir -p "$DATA_DIR"
    fi
    
    # Check database file
    if [ ! -f "$DATA_DIR/nostr_content.db" ]; then
        log_warning "Database file not found. It will be created on first run."
    fi
}

# Load configuration from environment or config file
load_config() {
    # Check for config file
    if [ -f "$RELAY_DIR/../config.py" ]; then
        log_info "Loading configuration from config.py..."
        
        # Extract values from Python config (improved parsing)
        NOSTR_NPUB=$(python3 -c "
import sys
sys.path.append('$RELAY_DIR/..')
try:
    from config import NOSTR_NPUB
    print(NOSTR_NPUB)
except:
    pass
" 2>/dev/null)
        
        RELAY_OWNER_ONLY=$(python3 -c "
import sys
sys.path.append('$RELAY_DIR/..')
try:
    from config import RELAY_OWNER_ONLY
    print('true' if RELAY_OWNER_ONLY else 'false')
except:
    print('true')
" 2>/dev/null)
        
        SITE_NAME=$(python3 -c "
import sys
sys.path.append('$RELAY_DIR/..')
try:
    from config import SITE_NAME
    print(SITE_NAME)
except:
    print('Nostr Home')
" 2>/dev/null)
        
        if [ -n "$NOSTR_NPUB" ]; then
            export NOSTR_NPUB
        fi
        
        if [ -n "$RELAY_OWNER_ONLY" ]; then
            export RELAY_OWNER_ONLY
        fi
        
        if [ -n "$SITE_NAME" ]; then
            export RELAY_NAME="$SITE_NAME Relay"
        fi
    fi
    
    # Set defaults if not configured
    export RELAY_PORT="${RELAY_PORT:-8080}"
    export RELAY_NAME="${RELAY_NAME:-Enhanced Personal Nostr Hub}"
    export RELAY_DESCRIPTION="${RELAY_DESCRIPTION:-Enhanced personal Nostr relay with multi-NIP support}"
    export RELAY_CONTACT="${RELAY_CONTACT:-admin@localhost}"
    export RELAY_OWNER_ONLY="${RELAY_OWNER_ONLY:-true}"
}

# Display current configuration
show_config() {
    echo
    log_info "=== Relay Configuration ==="
    echo "Port: ${RELAY_PORT}"
    echo "Name: ${RELAY_NAME}"
    echo "Description: ${RELAY_DESCRIPTION}"
    echo "Contact: ${RELAY_CONTACT}"
    echo "Owner Only: ${RELAY_OWNER_ONLY}"
    if [ -n "$NOSTR_NPUB" ]; then
        echo "Owner Npub: ${NOSTR_NPUB}"
    else
        log_warning "No owner npub configured (NOSTR_NPUB)"
    fi
    echo "Data Directory: ${DATA_DIR}"
    echo "Binary: ${BINARY_PATH}"
    echo
}

# Start the relay
start_relay() {
    log_info "Starting Enhanced Nostr Home Relay (Go)..."
    
    cd "$RELAY_DIR"
    exec "$BINARY_PATH"
}

# Build only
build_relay() {
    log_info "Building relay binary..."
    cd "$RELAY_DIR"
    
    if go build -o "$BINARY_NAME" main.go; then
        log_success "Relay binary built successfully: $BINARY_PATH"
    else
        log_error "Failed to build relay binary"
        exit 1
    fi
}

# Clean build artifacts
clean_relay() {
    log_info "Cleaning build artifacts..."
    cd "$RELAY_DIR"
    
    if [ -f "$BINARY_NAME" ]; then
        rm "$BINARY_NAME"
        log_success "Binary removed: $BINARY_NAME"
    fi
    
    if [ -d "vendor" ]; then
        rm -rf vendor
        log_success "Vendor directory removed"
    fi
    
    go clean -cache
    log_success "Go cache cleaned"
}

# Test relay functionality
test_relay() {
    log_info "Testing relay functionality..."
    
    # Check if relay is running
    if ! curl -s "http://localhost:${RELAY_PORT}/" > /dev/null; then
        log_error "Relay is not responding on port $RELAY_PORT"
        exit 1
    fi
    
    # Test relay info endpoint
    log_info "Testing relay info endpoint..."
    if curl -s "http://localhost:${RELAY_PORT}/" | grep -q "supported_nips"; then
        log_success "Relay info endpoint working"
    else
        log_error "Relay info endpoint failed"
        exit 1
    fi
    
    # Test stats endpoint
    log_info "Testing stats endpoint..."
    if curl -s "http://localhost:${RELAY_PORT}/relay/stats" | grep -q "connected_clients"; then
        log_success "Stats endpoint working"
    else
        log_error "Stats endpoint failed"
        exit 1
    fi
    
    log_success "All tests passed!"
}

# Show help
show_help() {
    echo "Enhanced Nostr Home Relay (Go) - Control Script"
    echo
    echo "Usage: $0 [OPTION]"
    echo
    echo "Options:"
    echo "  start     Start the relay server (default)"
    echo "  build     Build the relay binary only"
    echo "  clean     Clean build artifacts"
    echo "  test      Test relay functionality"
    echo "  config    Show current configuration"
    echo "  help      Show this help message"
    echo
    echo "Environment Variables:"
    echo "  RELAY_PORT           Port to run on (default: 8080)"
    echo "  NOSTR_NPUB           Owner's npub for owner-only mode"
    echo "  RELAY_OWNER_ONLY     Enable owner-only mode (default: true)"
    echo "  RELAY_NAME           Relay name (default: Enhanced Personal Nostr Hub)"
    echo "  RELAY_DESCRIPTION    Relay description"
    echo "  RELAY_CONTACT        Contact information"
    echo
    echo "Examples:"
    echo "  $0                            # Start with default config"
    echo "  $0 build                      # Build binary only"
    echo "  RELAY_PORT=8081 $0 start      # Start on port 8081"
    echo "  NOSTR_NPUB=npub1... $0 start  # Start with owner npub"
    echo
}

# Main script logic
main() {
    case "${1:-start}" in
        start)
            check_binary
            setup_data_dir
            load_config
            show_config
            start_relay
            ;;
        build)
            build_relay
            ;;
        clean)
            clean_relay
            ;;
        test)
            load_config
            test_relay
            ;;
        config)
            load_config
            show_config
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown option: $1"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Check dependencies
check_dependencies() {
    if ! command -v go &> /dev/null; then
        log_error "Go is not installed or not in PATH"
        echo "Please install Go 1.21+ from https://golang.org/dl/"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log_warning "curl is not installed (needed for testing)"
    fi
}

# Initialize
cd "$RELAY_DIR"
check_dependencies
main "$@"
