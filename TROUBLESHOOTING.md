# Troubleshooting

## Common Issues

### Missing dependencies
```bash
pip install -e ".[full,nostr,dev]"
```

### PHANTOM mode fails
Ensure you are using v2.1.3 or later. Earlier versions had a fixed RNG seed that broke roundtrips.

### Delta validation errors
Since v2.1.3, delta values outside [0.5, 50.0] raise ValueError instead of being silently clamped.

### Path traversal protection
The engine now rejects paths containing `..` or pointing to system directories.
