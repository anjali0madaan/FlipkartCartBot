# Flipkart iPhone Automation Tool

## Overview

This project is a web automation tool designed to search and monitor iPhone products on Flipkart, India's popular e-commerce platform. The system uses Selenium WebDriver to automate browser interactions, enabling users to search for specific iPhone models within defined price ranges and apply various filters. The tool is configured through JSON files and provides logging capabilities to track automation activities.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Application Structure
The project follows a modular architecture with three main components:
- **Configuration Layer**: JSON-based configuration system for search parameters, automation settings, and user preferences
- **Core Automation Engine**: Selenium WebDriver-based automation class that handles web scraping and interaction
- **Command-Line Interface**: User-friendly launcher script with argument parsing and interactive prompts

### Design Patterns
- **Configuration-Driven Design**: All automation parameters are externalized to a JSON configuration file, making the system flexible and easily customizable without code changes
- **Class-Based Architecture**: The main automation logic is encapsulated in a `FlipkartAutomation` class with clear separation of concerns
- **Error Handling Strategy**: Implements retry mechanisms and comprehensive exception handling for robust web automation
- **Logging Framework**: Integrated logging system with both file and console output for debugging and monitoring

### Web Automation Strategy
- **Selenium WebDriver**: Uses Chrome WebDriver for reliable browser automation with configurable options for headless operation
- **Explicit Waits**: Implements WebDriverWait for handling dynamic content loading and ensuring element availability
- **Timeout Management**: Configurable timeout settings for page loads and element interactions

### Configuration Management
- **Flexible Search Parameters**: Supports product name, price ranges, search queries, and brand filters
- **Automation Controls**: Configurable wait times, retry limits, and browser mode settings
- **User Authentication**: Placeholder for email/password credentials (currently empty)
- **Filter System**: Built-in support for sorting, condition filtering, and brand-specific searches

## External Dependencies

### Core Dependencies
- **Selenium WebDriver**: Primary automation framework for browser control and web interaction
- **Chrome Browser**: Target browser for automation (requires ChromeDriver)

### Python Standard Library
- **json**: Configuration file parsing and data serialization
- **logging**: Comprehensive logging system for automation tracking
- **time**: Wait and delay mechanisms for automation timing
- **argparse**: Command-line argument parsing for the launcher script
- **os**: Environment variable access and file system operations
- **sys**: System-specific parameters and functions
- **re**: Regular expression support for text parsing

### Target Platform
- **Flipkart.com**: Indian e-commerce platform being automated
- **Chrome WebDriver**: Browser automation driver (requires separate installation)

### Development Tools
- **Type Hints**: Uses Python typing module for better code documentation and IDE support
- **File I/O**: JSON configuration files for persistent settings storage