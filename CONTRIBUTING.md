# Contributing

Thank you for your interest in contributing to Stegstr!

## Development Setup

```bash
git clone https://github.com/Juani1972/steganography.git
cd steganography
pip install -e ".[full,nostr,dev]"
```

## Running Tests

```bash
pytest tests/ -v
python validate.py
```

## Code Style

We use black and isort:

```bash
black stegstr/ tests/
isort stegstr/ tests/
```
