# Repository Reorganization Summary

## Overview
This PR reorganizes the repository to keep `worker_pool_v3` as the main architecture while improving code organization, security, and maintainability.

## Changes Made

### 1. Directory Structure Created
- **src/** - All production source code
  - **src/server/** - API server components
  - **src/workers/** - Worker pool implementations
  - **src/solvers/** - CAPTCHA solving modules
  - **src/cluster/** - Cluster management components
- **configs/** - Configuration files (with sensitive data excluded from git)
- **deploy/** - Deployment scripts
- **archive/** - Legacy, debug, and free versions (kept for reference)

### 2. Production Files Moved to src/
- `api_server.py` → `src/server/api_server.py`
- `worker_pool_v3.py` → `src/workers/worker_pool_v3.py`
- `captcha_solver.py` → `src/solvers/captcha_solver.py`
- `captcha_solver_free.py` → `src/solvers/captcha_solver_free.py`
- `cluster_master.py` → `src/cluster/cluster_master.py`
- `cluster_worker.py` → `src/cluster/cluster_worker.py`
- `cluster_monitor.py` → `src/cluster/cluster_monitor.py`

### 3. Legacy/Debug Files Archived
Moved to `archive/` directory:
- `worker_pool.py` → `archive/worker_pool_legacy.py`
- `worker_pool_v2.py` → `archive/worker_pool_v2.py`
- `worker_pool_free.py` → `archive/worker_pool_free.py`
- `debug_*.py` and `debug_*.html` files
- `test_positions.py` and `test_v2.py`
- `deploy.sh` (old deployment script)

### 4. Deployment Scripts Organized
Moved to `deploy/` directory:
- `deploy_agora.sh`
- `deploy_single_server.sh`
- `install_all.sh`

### 5. Security Improvements
**Sensitive files removed from git tracking:**
- `wit_keys.txt` → moved to `configs/wit_keys.txt` (git-ignored)
- `captcha_tokens.txt` → moved to `configs/captcha_tokens.txt` (git-ignored)

**New security files:**
- `.gitignore` - Comprehensive ignore rules including sensitive configs
- `configs/.env.example` - Template for environment variables (no secrets)

⚠️ **SECURITY NOTICE**: If `wit_keys.txt` or `captcha_tokens.txt` were previously committed, the API keys should be rotated immediately as they may have been exposed in the git history.

### 6. Import Path Updates
Updated imports to reflect new structure:
- `src/server/api_server.py`: `from src.workers.worker_pool_v3 import WorkerPool`
- `src/workers/worker_pool_v3.py`: Updated to import from `src.solvers.*`

### 7. Backward Compatibility
Created wrapper files in the root for legacy compatibility:
- `worker_pool_v3.py` - Imports from `src.workers.worker_pool_v3`
- `captcha_solver.py` - Imports from `src.solvers.captcha_solver`
- `captcha_solver_free.py` - Imports from `src.solvers.captcha_solver_free`

This allows existing scripts to continue using:
```python
from worker_pool_v3 import WorkerPool
```

### 8. Documentation Added
- `README.md` - Comprehensive project documentation
- `configs/README.md` - Configuration setup instructions

## How to Run After Changes

### Option 1: Using PYTHONPATH (Recommended)
```bash
export PYTHONPATH=/path/to/SEARCH_API_GOOGLE:$PYTHONPATH
python3 src/server/api_server.py
```

### Option 2: Using backward compatibility wrappers
```bash
# Still works without PYTHONPATH
python3 -c "from worker_pool_v3 import WorkerPool; print('Works!')"
```

### Setup Configuration
1. Copy the example environment file:
```bash
cp configs/.env.example .env
```

2. Create your API key files:
```bash
# Add your Wit.ai keys (one per line)
vim configs/wit_keys.txt

# Add your 2Captcha tokens (one per line)
vim configs/captcha_tokens.txt
```

3. Set environment variables (or use .env file):
```bash
export CAPTCHA_TOKEN_FILE=configs/captcha_tokens.txt
export WIT_AI_TOKEN=your_wit_ai_token
export SELENIUM_WORKERS=1
```

## Testing

All imports have been verified to work correctly:
- ✅ Direct imports from `src.*` structure work
- ✅ Backward compatibility wrappers work
- ✅ Sensitive files are properly excluded from git
- ✅ Python package structure is correct (__init__.py files added)

## Files Changed
- 36 files changed
- 1,500 insertions
- 1,278 deletions
- Net: +222 lines (mostly documentation and structure)

## Migration Notes

### For Developers
- Update your PYTHONPATH to include the project root
- Import from the new structure: `from src.workers.worker_pool_v3 import WorkerPool`
- Or continue using the root wrappers for backward compatibility

### For Deployment
- Ensure `configs/wit_keys.txt` and `configs/captcha_tokens.txt` exist on production servers
- These files are no longer in git and must be deployed separately
- Consider using environment variables or secret management systems

### Breaking Changes
None! The backward compatibility wrappers ensure existing code continues to work.

## Security Actions Required

🔒 **ACTION REQUIRED**: Since `wit_keys.txt` and `captcha_tokens.txt` were previously committed to git:
1. Rotate all API keys and tokens immediately
2. Update the new keys in `configs/wit_keys.txt` and `configs/captcha_tokens.txt`
3. Ensure these files are never committed again (they're now in .gitignore)

## Commits
1. `chore(reorg): keep worker_pool_v3 as main; move production files to src/; archive free/legacy/debug; remove keys from git index; add configs/.env.example`
2. `docs: add README files explaining new structure and configuration`
