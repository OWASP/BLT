#!/bin/bash

# BLT Extension Installer
# This script downloads and installs the OWASP BLT Extension for Chrome/Chromium browsers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# GitHub repository info
REPO_OWNER="OWASP-BLT"
REPO_NAME="BLT-Extension"
GITHUB_API="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/releases/latest"
EXTENSION_PAGE="https://owasp.org/www-project-bug-logging-tool/"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   OWASP BLT Extension Installer${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     OS="Linux";;
        Darwin*)    OS="macOS";;
        CYGWIN*|MINGW*|MSYS*) OS="Windows";;
        *)          OS="Unknown";;
    esac
    echo -e "${GREEN}Detected OS: ${OS}${NC}"
}

# Find Chrome/Chromium profile directories
find_chrome_profiles() {
    PROFILES=()
    PROFILE_PATHS=()
    
    case "$OS" in
        Linux)
            # Chrome profiles
            if [ -d "$HOME/.config/google-chrome" ]; then
                for profile in "$HOME/.config/google-chrome"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Chrome - $profile_name")
                        PROFILE_PATHS+=("$HOME/.config/google-chrome/$profile_name")
                    fi
                done
            fi
            # Chromium profiles
            if [ -d "$HOME/.config/chromium" ]; then
                for profile in "$HOME/.config/chromium"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Chromium - $profile_name")
                        PROFILE_PATHS+=("$HOME/.config/chromium/$profile_name")
                    fi
                done
            fi
            # Brave Browser profiles
            if [ -d "$HOME/.config/BraveSoftware/Brave-Browser" ]; then
                for profile in "$HOME/.config/BraveSoftware/Brave-Browser"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Brave - $profile_name")
                        PROFILE_PATHS+=("$HOME/.config/BraveSoftware/Brave-Browser/$profile_name")
                    fi
                done
            fi
            # Edge profiles
            if [ -d "$HOME/.config/microsoft-edge" ]; then
                for profile in "$HOME/.config/microsoft-edge"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Edge - $profile_name")
                        PROFILE_PATHS+=("$HOME/.config/microsoft-edge/$profile_name")
                    fi
                done
            fi
            ;;
        macOS)
            # Chrome profiles
            if [ -d "$HOME/Library/Application Support/Google/Chrome" ]; then
                for profile in "$HOME/Library/Application Support/Google/Chrome"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Chrome - $profile_name")
                        PROFILE_PATHS+=("$HOME/Library/Application Support/Google/Chrome/$profile_name")
                    fi
                done
            fi
            # Chromium profiles
            if [ -d "$HOME/Library/Application Support/Chromium" ]; then
                for profile in "$HOME/Library/Application Support/Chromium"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Chromium - $profile_name")
                        PROFILE_PATHS+=("$HOME/Library/Application Support/Chromium/$profile_name")
                    fi
                done
            fi
            # Brave Browser profiles
            if [ -d "$HOME/Library/Application Support/BraveSoftware/Brave-Browser" ]; then
                for profile in "$HOME/Library/Application Support/BraveSoftware/Brave-Browser"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Brave - $profile_name")
                        PROFILE_PATHS+=("$HOME/Library/Application Support/BraveSoftware/Brave-Browser/$profile_name")
                    fi
                done
            fi
            # Edge profiles
            if [ -d "$HOME/Library/Application Support/Microsoft Edge" ]; then
                for profile in "$HOME/Library/Application Support/Microsoft Edge"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Edge - $profile_name")
                        PROFILE_PATHS+=("$HOME/Library/Application Support/Microsoft Edge/$profile_name")
                    fi
                done
            fi
            ;;
        Windows)
            # Chrome profiles
            if [ -d "$LOCALAPPDATA/Google/Chrome/User Data" ]; then
                for profile in "$LOCALAPPDATA/Google/Chrome/User Data"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Chrome - $profile_name")
                        PROFILE_PATHS+=("$LOCALAPPDATA/Google/Chrome/User Data/$profile_name")
                    fi
                done
            fi
            # Chromium profiles
            if [ -d "$LOCALAPPDATA/Chromium/User Data" ]; then
                for profile in "$LOCALAPPDATA/Chromium/User Data"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Chromium - $profile_name")
                        PROFILE_PATHS+=("$LOCALAPPDATA/Chromium/User Data/$profile_name")
                    fi
                done
            fi
            # Brave Browser profiles
            if [ -d "$LOCALAPPDATA/BraveSoftware/Brave-Browser/User Data" ]; then
                for profile in "$LOCALAPPDATA/BraveSoftware/Brave-Browser/User Data"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Brave - $profile_name")
                        PROFILE_PATHS+=("$LOCALAPPDATA/BraveSoftware/Brave-Browser/User Data/$profile_name")
                    fi
                done
            fi
            # Edge profiles
            if [ -d "$LOCALAPPDATA/Microsoft/Edge/User Data" ]; then
                for profile in "$LOCALAPPDATA/Microsoft/Edge/User Data"/*/; do
                    if [ -f "${profile}Preferences" ]; then
                        profile_name=$(basename "$profile")
                        PROFILES+=("Edge - $profile_name")
                        PROFILE_PATHS+=("$LOCALAPPDATA/Microsoft/Edge/User Data/$profile_name")
                    fi
                done
            fi
            ;;
    esac
}

# Get the browser data directory from profile path
get_browser_data_dir() {
    local profile_path="$1"
    dirname "$profile_path"
}

# Get the browser executable
get_browser_executable() {
    local profile_name="$1"
    local browser_type="${profile_name%% - *}"
    
    case "$OS" in
        Linux)
            case "$browser_type" in
                Chrome)     echo "google-chrome";;
                Chromium)   echo "chromium-browser";;
                Brave)      echo "brave-browser";;
                Edge)       echo "microsoft-edge";;
            esac
            ;;
        macOS)
            case "$browser_type" in
                Chrome)     echo "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";;
                Chromium)   echo "/Applications/Chromium.app/Contents/MacOS/Chromium";;
                Brave)      echo "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser";;
                Edge)       echo "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge";;
            esac
            ;;
        Windows)
            case "$browser_type" in
                Chrome)     echo "chrome.exe";;
                Chromium)   echo "chromium.exe";;
                Brave)      echo "brave.exe";;
                Edge)       echo "msedge.exe";;
            esac
            ;;
    esac
}

# Download the latest release
download_extension() {
    echo -e "${YELLOW}Fetching latest release information...${NC}"
    
    # Create temp directory
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # Try to get the latest release
    RELEASE_INFO=$(curl -s "$GITHUB_API" 2>/dev/null || echo "")
    
    if [ -z "$RELEASE_INFO" ] || echo "$RELEASE_INFO" | grep -q "Not Found"; then
        echo -e "${YELLOW}No releases found. Downloading from main branch...${NC}"
        # Download from main branch as a zip
        curl -sL "https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/heads/main.zip" -o extension.zip
        unzip -q extension.zip
        mv "${REPO_NAME}-main" blt-extension
    else
        # Get the download URL for the zip asset
        DOWNLOAD_URL=$(echo "$RELEASE_INFO" | grep -o '"browser_download_url": *"[^"]*\.zip"' | head -1 | sed 's/"browser_download_url": *"//' | sed 's/"$//')
        
        if [ -z "$DOWNLOAD_URL" ]; then
            echo -e "${YELLOW}No zip asset found in release. Downloading source...${NC}"
            ZIPBALL_URL=$(echo "$RELEASE_INFO" | grep -o '"zipball_url": *"[^"]*"' | head -1 | sed 's/"zipball_url": *"//' | sed 's/"$//')
            curl -sL "$ZIPBALL_URL" -o extension.zip
            unzip -q extension.zip
            mv "${REPO_OWNER}-${REPO_NAME}"* blt-extension
        else
            echo -e "${GREEN}Downloading release from: ${DOWNLOAD_URL}${NC}"
            curl -sL "$DOWNLOAD_URL" -o extension.zip
            unzip -q extension.zip -d blt-extension
        fi
    fi
    
    EXTENSION_DIR="$TEMP_DIR/blt-extension"
    echo -e "${GREEN}Extension downloaded to: ${EXTENSION_DIR}${NC}"
}

# Install the extension
install_extension() {
    local profile_path="$1"
    local profile_name="$2"
    
    # Create Extensions directory if it doesn't exist
    EXTENSIONS_DIR="${profile_path}/Extensions"
    mkdir -p "$EXTENSIONS_DIR"
    
    # Generate a unique extension ID (based on the extension path)
    # For unpacked extensions, we'll install to a known location
    INSTALL_DIR="${EXTENSIONS_DIR}/owasp-blt-extension"
    
    # Copy extension files
    echo -e "${YELLOW}Installing extension to: ${INSTALL_DIR}${NC}"
    rm -rf "$INSTALL_DIR" 2>/dev/null || true
    cp -r "$EXTENSION_DIR" "$INSTALL_DIR"
    
    echo -e "${GREEN}Extension files copied successfully!${NC}"
    
    # Store the install directory for later use
    INSTALLED_DIR="$INSTALL_DIR"
}

# Launch browser with extension
launch_browser() {
    local profile_path="$1"
    local profile_name="$2"
    local browser_exe
    browser_exe=$(get_browser_executable "$profile_name")
    local actual_profile_name="${profile_name#* - }"
    
    echo -e "${YELLOW}Launching browser...${NC}"
    
    # Kill existing browser processes (optional, with user confirmation)
    echo -e "${YELLOW}Note: For the extension to load, you may need to:${NC}"
    echo -e "${YELLOW}1. Close all browser windows${NC}"
    echo -e "${YELLOW}2. Go to chrome://extensions${NC}"
    echo -e "${YELLOW}3. Enable 'Developer mode'${NC}"
    echo -e "${YELLOW}4. Click 'Load unpacked' and select: ${INSTALLED_DIR}${NC}"
    echo ""
    
    read -rp "Would you like to open the browser now? (y/n): " open_browser
    
    if [ "$open_browser" = "y" ] || [ "$open_browser" = "Y" ]; then
        case "$OS" in
            Linux)
                if command -v "$browser_exe" &> /dev/null; then
                    "$browser_exe" --profile-directory="$actual_profile_name" "$EXTENSION_PAGE" &
                else
                    echo -e "${RED}Browser executable not found: ${browser_exe}${NC}"
                fi
                ;;
            macOS)
                if [ -f "$browser_exe" ]; then
                    "$browser_exe" --profile-directory="$actual_profile_name" "$EXTENSION_PAGE" &
                else
                    echo -e "${RED}Browser executable not found: ${browser_exe}${NC}"
                fi
                ;;
            Windows)
                start "" "$browser_exe" --profile-directory="$actual_profile_name" "$EXTENSION_PAGE" &
                ;;
        esac
        
        echo -e "${GREEN}Browser launched!${NC}"
    fi
}

# Main function
main() {
    # Check for required commands
    for cmd in curl unzip; do
        if ! command -v "$cmd" &> /dev/null; then
            echo -e "${RED}Error: '$cmd' is required but not installed.${NC}"
            exit 1
        fi
    done
    
    # Detect operating system
    detect_os
    
    if [ "$OS" = "Unknown" ]; then
        echo -e "${RED}Error: Unsupported operating system${NC}"
        exit 1
    fi
    
    # Find Chrome/Chromium profiles
    echo -e "${YELLOW}Searching for browser profiles...${NC}"
    find_chrome_profiles
    
    if [ ${#PROFILES[@]} -eq 0 ]; then
        echo -e "${RED}No Chrome/Chromium profiles found.${NC}"
        echo -e "${YELLOW}Please install Chrome or Chromium and create a profile first.${NC}"
        exit 1
    fi
    
    # Display profiles
    echo ""
    echo -e "${GREEN}Found ${#PROFILES[@]} browser profile(s):${NC}"
    echo ""
    for i in "${!PROFILES[@]}"; do
        echo "  $((i+1)). ${PROFILES[$i]}"
    done
    echo ""
    
    # Let user select profile
    while true; do
        read -rp "Select a profile (1-${#PROFILES[@]}): " selection
        if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le ${#PROFILES[@]} ]; then
            break
        fi
        echo -e "${RED}Invalid selection. Please enter a number between 1 and ${#PROFILES[@]}.${NC}"
    done
    
    selected_index=$((selection-1))
    selected_profile="${PROFILES[$selected_index]}"
    selected_path="${PROFILE_PATHS[$selected_index]}"
    
    echo ""
    echo -e "${GREEN}Selected: ${selected_profile}${NC}"
    echo -e "${GREEN}Path: ${selected_path}${NC}"
    echo ""
    
    # Download extension
    download_extension
    
    # Install extension
    install_extension "$selected_path" "$selected_profile"
    
    # Launch browser
    launch_browser "$selected_path" "$selected_profile"
    
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}Installation complete!${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${YELLOW}To finish setup:${NC}"
    echo -e "1. Open your browser and go to ${BLUE}chrome://extensions${NC}"
    echo -e "2. Enable ${BLUE}Developer mode${NC} (toggle in top right)"
    echo -e "3. Click ${BLUE}Load unpacked${NC}"
    echo -e "4. Select the folder: ${GREEN}${INSTALLED_DIR}${NC}"
    echo ""
    echo -e "Visit ${BLUE}${EXTENSION_PAGE}${NC} to learn more about BLT!"
    
    # Cleanup temp files (keep extension files)
    rm -f "$TEMP_DIR/extension.zip" 2>/dev/null || true
}

# Run main function
main "$@"
