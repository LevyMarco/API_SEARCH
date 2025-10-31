# SEARCH_API_GOOGLE

Google Search API with CAPTCHA solving capabilities using Selenium and undetected-chromedriver.

## Project Structure

```
.
├── src/                          # Production source code
│   ├── server/                   # API server
│   │   └── api_server.py        # Flask API server
│   ├── workers/                  # Worker pool implementations
│   │   └── worker_pool_v3.py    # Main worker pool (V3)
│   ├── solvers/                  # CAPTCHA solving modules
│   │   ├── captcha_solver.py    # 2Captcha paid solver
│   │   └── captcha_solver_free.py # Wit.ai free solver
│   └── cluster/                  # Cluster management
│       ├── cluster_master.py
│       ├── cluster_worker.py
│       └── cluster_monitor.py
├── configs/                      # Configuration files (git-ignored keys)
│   ├── .env.example             # Environment variables template
│   ├── wit_keys.txt             # Wit.ai API keys (not in git)
│   └── captcha_tokens.txt       # 2Captcha tokens (not in git)
├── deploy/                       # Deployment scripts
│   ├── deploy_agora.sh
│   ├── deploy_single_server.sh
│   └── install_all.sh
├── archive/                      # Legacy/debug files (not used in production)
│   ├── worker_pool_legacy.py
│   ├── worker_pool_v2.py
│   ├── worker_pool_free.py
│   └── debug_*.py/html
├── worker_pool_v3.py            # Backward compatibility wrapper
├── captcha_solver.py            # Backward compatibility wrapper
└── captcha_solver_free.py       # Backward compatibility wrapper
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up configuration:
```bash
cp configs/.env.example .env
# Edit .env with your settings
```

3. Add your API keys:
- Create `configs/wit_keys.txt` with Wit.ai keys (one per line)
- Create `configs/captcha_tokens.txt` with 2Captcha tokens (one per line)

## Running the Application

### Set PYTHONPATH

For the new structure to work, add the project root to PYTHONPATH:

```bash
export PYTHONPATH=/path/to/SEARCH_API_GOOGLE:$PYTHONPATH
```

### Start the API Server

```bash
python3 src/server/api_server.py
```

Or use backward compatibility wrappers (works without PYTHONPATH):

```bash
python3 -c "from src.server.api_server import app; app.run()"
```

## Backward Compatibility

The root directory contains wrapper files for backward compatibility:
- `worker_pool_v3.py` → imports from `src.workers.worker_pool_v3`
- `captcha_solver.py` → imports from `src.solvers.captcha_solver`
- `captcha_solver_free.py` → imports from `src.solvers.captcha_solver_free`

Legacy scripts can continue to use:
```python
from worker_pool_v3 import WorkerPool
```

## Security Notice

⚠️ **IMPORTANT**: API keys and tokens are now stored in the `configs/` directory and are excluded from git tracking. If keys were previously committed to the repository, **rotate them immediately** as they may have been exposed.

## Development

The main production code is in `src/` with the following architecture:
- **worker_pool_v3** is the current production implementation
- Legacy versions (v1, v2, free) are archived for reference
- Debug scripts are archived and not used in production

## Deployment

Deployment scripts are located in `deploy/`:
- `deploy_agora.sh` - Current deployment script
- `deploy_single_server.sh` - Single server deployment
- `install_all.sh` - Installation script

## Requirements

- Python 3.7+
- Chrome/Chromium browser
- See `requirements.txt` for Python dependencies
