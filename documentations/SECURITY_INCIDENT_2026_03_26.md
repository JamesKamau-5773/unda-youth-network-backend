# Security Incident - Database Credentials Exposed

**Date:** 2026-03-26  
**Severity:** HIGH  
**Status:** RESOLVED with FUTURE PREVENTION

## Incident Summary

GitGuardian detected database credentials exposed in GitHub repository history via `.env.example`. The PostgreSQL URI contained plaintext password and connection details.

## What Happened

- Real database credentials were committed to `.env.example` on lines 21-24
- File was tracked in git history across multiple commits
- Credentials were publicly visible in GitHub repository

## Actions Taken

### ✅ Immediate Mitigation
1. **Removed credentials from `.env.example`** - Replaced with placeholder values
2. **Scrubbed git history** - Used `git-filter-repo` to remove all instances of the password from all commits
3. **Force pushed cleaned history** to GitHub

### ✅ Password Rotation Required
**⚠️ IMPORTANT:** The exposed database password must be rotated immediately:

1. Go to Render dashboard
2. Navigate to your PostgreSQL database instance  
3. Reset the password for `unda_db_user`
4. Update `DATABASE_URL` in Render environment variables with new password
5. Redeploy your application

**The old password is now compromised and should NOT be used.**

### ✅ Future Prevention

#### 1. Enhanced `.gitignore`
Added comprehensive patterns to prevent future credential leaks:
- All `.env*` files (except `.env.example`)
- Private keys, certificates, credentials files
- API keys and secrets
- AWS credentials and SSH keys

#### 2. Pre-commit Hook
Created `.git/hooks/pre-commit` that:
- Detects database URIs, API keys, and passwords before commit
- Blocks commits containing secrets
- Allows override with `--no-verify` only when intentional
- Allows `.env.example` (placeholders) but blocks `.env`

## Best Practices Going Forward

### ✅ DO:
- Use `.env.example` with **PLACEHOLDER** values only
- Store real credentials in environment variables (Render, CI/CD, etc.)
- Review files before committing: `git diff --cached`
- Use secrets management tools (Render's built-in env vars, HashiCorp Vault, AWS Secrets Manager)
- Rotate compromised credentials immediately

### ❌ DON'T:
- Commit `.env` files to git
- Put real passwords in config files tracked by git
- Share credentials via pull requests or git history
- Commit API keys, tokens, or private keys

## Verification

Run these commands to verify protections:

```bash
# Test pre-commit hook (will block if secrets detected)
git commit -m "test" --allow-empty

# View files ignored by git
git check-ignore -v *.*

# Verify no secrets in recent history
git log -p HEAD~5 | grep -i "password\|api_key\|secret"
```

## References

- [Git Secrets Best Practices](https://docs.github.com/en/code-security/secret-scanning)
- [Render Environment Variables](https://render.com/docs/environment-variables)
- [Pre-commit Hooks](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)
- [GitGuardian](https://www.gitguardian.com/)

---

**Status:** Closed - All preventive measures implemented
