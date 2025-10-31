# Configuration Directory

This directory contains configuration files for the SEARCH_API_GOOGLE project.

## Files

### .env.example
Template for environment variables. Copy this to `.env` and fill in your actual values:
```bash
cp configs/.env.example .env
```

### wit_keys.txt (not in git)
Contains Wit.ai API keys for free CAPTCHA solving, one per line.
This file is kept locally and not committed to git.

### captcha_tokens.txt (not in git)
Contains 2Captcha API tokens, one per line.
This file is kept locally and not committed to git.

## Security Note

⚠️ **IMPORTANT**: The files `wit_keys.txt` and `captcha_tokens.txt` contain sensitive API keys and should NEVER be committed to git. They are listed in `.gitignore` to prevent accidental commits.

If these files were previously committed to the repository, the keys should be rotated immediately as they may have been exposed.

## Usage

When running the application, you can reference these config files via environment variables:
```bash
export CAPTCHA_TOKEN_FILE=configs/captcha_tokens.txt
export WIT_AI_TOKEN=<your_wit_ai_token>
```

Or use the `.env` file for easier configuration management.
