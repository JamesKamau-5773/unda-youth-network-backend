# Rate Limiting Fix Plan

## Problem Analysis
The test `test_rate_limiting_tc_3_2_fifth_attempt_blocked` is failing because:
1. Rate limiting is not properly applied to the login route
2. The current implementation tries to apply rate limiting in `set_limiter()` but it's not working correctly
3. The rate limiting should specifically track failed login attempts, not all login attempts

## Current Issues
1. In `blueprints/auth.py`, the rate limiting decorator is applied in `set_limiter()` but the logic is incomplete
2. The rate limiting should be applied directly to the login route
3. Need to track failed login attempts specifically, not successful ones
4. The test expects 429 status code on the 5th failed attempt

## Fix Plan

### Step 1: Fix Rate Limiting in auth.py
- Apply `@limiter.limit()` decorator directly to the login route
- Configure it to allow 4 attempts per minute, then rate limit the 5th
- Ensure it returns 429 status code on rate limit

### Step 2: Test the Fix
- Run the failing test to verify it passes
- Ensure other rate limiting tests still work

### Step 3: Verify Integration
- Check that successful logins don't count towards the rate limit
- Verify the rate limiting works with in-memory storage for tests
