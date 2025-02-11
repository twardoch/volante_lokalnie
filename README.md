# Volante Lokalnie

A modern Python CLI tool for managing offers on Allegro Lokalnie, providing automation for common tasks like bulk updating listings and managing offer descriptions.

## 🚀 TLDR

```bash
uv pip install git+https://github.com/twardoch/volante_lokalnie/
python -m volante_lokalnie --help
```

## 🎯 Purpose & Background

Managing multiple listings on Allegro Lokalnie can be time-consuming, especially when you need to update descriptions, titles, or monitor views across multiple offers. This tool automates these tasks through a command-line interface, making it easier to:

- Fetch and monitor all your active offers
- Bulk update offer titles and descriptions
- Track offer statistics (views, prices)
- Manage offer content with local storage
- Automate repetitive listing management tasks

## ✨ Features

- **Modern Python Implementation**
  - Type hints and runtime type checking
  - PEP 621 compliant packaging
  - Comprehensive test suite
  - CI/CD ready configuration

- **Offer Management**
  - Fetch and store active offers locally
  - Read and update offer descriptions
  - Update offer titles
  - Track offer statistics
  - Bulk operations support

- **Smart Automation**
  - Template support for titles and descriptions
  - Automatic offer synchronization
  - Local database for tracking changes
  - Dry-run mode for testing changes

## 📦 Installation

```bash
# Using uv
uv pip install git+https://github.com/twardoch/volante_lokalnie/

# Using pip
pip install git+https://github.com/twardoch/volante_lokalnie/

# For development (requires Hatch)
pip install hatch
git clone https://github.com/twardoch/volante_lokalnie.git
cd volante_lokalnie
hatch shell
```

## 🔧 Usage

### Basic Commands

```bash
# Fetch all active offers
python -m volante_lokalnie fetch

# Read details for a specific offer
python -m volante_lokalnie read OFFER_ID

# Update an offer's title
python -m volante_lokalnie set-title OFFER_ID "New Title"

# Update an offer's description
python -m volante_lokalnie set-desc OFFER_ID "New Description"

# Refresh all offers and their descriptions
python -m volante_lokalnie read-all

# Publish pending changes for all modified offers
python -m volante_lokalnie publish-all
```

### Global Options

```bash
# Enable verbose logging
python -m volante_lokalnie --verbose fetch

# Show what would be done without making changes
python -m volante_lokalnie --dryrun publish-all

# Reset pending changes when fetching
python -m volante_lokalnie --reset fetch
```

## 🛠️ Development

This project uses [Hatch](https://hatch.pypa.io/) for development workflow management.

```bash
# Create and activate development environment
hatch shell

# Run tests
hatch run test

# Run tests with coverage
hatch run test-cov

# Run linting
hatch run lint

# Format code
hatch run format
```

## 📄 License

MIT License - See LICENSE file for details.

## 📝 Author

Adam Twardoch (adam+github@twardoch.com)

## 🔗 Links

- [Documentation](https://github.com/twardoch/volante_lokalnie#readme)
- [Issues](https://github.com/twardoch/volante_lokalnie/issues)
- [Source](https://github.com/twardoch/volante_lokalnie) 