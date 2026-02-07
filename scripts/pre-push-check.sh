#!/bin/bash
# Pre-push validation script
# Place in: .git/hooks/pre-push
# Make executable: chmod +x .git/hooks/pre-push

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🔍 Pre-Push Validation${NC}"
echo -e "${BLUE}========================================${NC}"

# Get branch name
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "\n${BLUE}📌 Branch: $BRANCH${NC}"

# 1. Check for hardcoded secrets
echo -e "\n${BLUE}1️⃣  Scanning for hardcoded secrets...${NC}"
if grep -r "password\|secret\|api_key\|token" app/ tests/ --include="*.py" 2>/dev/null | grep -v "# " | grep -v "PASSWORD\|SECRET\|API_KEY\|TOKEN" | grep -iE "password\s*=|secret\s*=|api_key\s*=|token\s*=" 2>/dev/null; then
    echo -e "${RED}❌ Found potential hardcoded secrets!${NC}"
    echo -e "${YELLOW}⚠️  Use environment variables instead.${NC}"
    exit 1
else
    echo -e "${GREEN}✅ No hardcoded secrets detected${NC}"
fi

# 2. Check for untracked files
echo -e "\n${BLUE}2️⃣  Checking for untracked sensitive files...${NC}"
if [ -f ".env" ] && ! git check-ignore ".env" > /dev/null; then
    echo -e "${RED}❌ .env file is tracked! It should be in .gitignore${NC}"
    exit 1
fi
if [ -f ".env.local" ] && ! git check-ignore ".env.local" > /dev/null; then
    echo -e "${RED}❌ .env.local file is tracked! It should be in .gitignore${NC}"
    exit 1
fi
echo -e "${GREEN}✅ No untracked sensitive files${NC}"

# 3. Run unit tests (quick)
echo -e "\n${BLUE}3️⃣  Running quick unit tests...${NC}"
if ! pytest tests/test_core.py tests/test_main.py -q --tb=short --timeout=10 2>/dev/null; then
    echo -e "${RED}❌ Unit tests failed!${NC}"
    echo -e "${YELLOW}⚠️  Fix failing tests before pushing${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Unit tests passed${NC}"
fi

# 4. Check code format
echo -e "\n${BLUE}4️⃣  Checking code format...${NC}"
if command -v black &> /dev/null; then
    if ! black --check app/ tests/ --quiet 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Code needs formatting${NC}"
        echo -e "${BLUE}💡 Run: make format${NC}"
        # Don't exit, just warn
    else
        echo -e "${GREEN}✅ Code format is correct${NC}"
    fi
fi

# 5. Check imports
echo -e "\n${BLUE}5️⃣  Checking imports...${NC}"
if command -v isort &> /dev/null; then
    if ! isort --check-only app/ tests/ --quiet 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Imports need sorting${NC}"
        echo -e "${BLUE}💡 Run: make format${NC}"
        # Don't exit, just warn
    else
        echo -e "${GREEN}✅ Imports are sorted${NC}"
    fi
fi

# 6. Check for large files
echo -e "\n${BLUE}6️⃣  Checking for large files...${NC}"
LARGE_FILES=$(git diff --cached --name-only | while read file; do
    SIZE=$(git cat-file -s :0:$file 2>/dev/null || echo 0)
    if [ $SIZE -gt 5242880 ]; then  # 5MB
        echo "$file ($((SIZE / 1024 / 1024))MB)"
    fi
done)
if [ -n "$LARGE_FILES" ]; then
    echo -e "${YELLOW}⚠️  Large files detected:${NC}"
    echo "$LARGE_FILES"
    echo -e "${YELLOW}⚠️  Consider using Git LFS for large files${NC}"
fi
echo -e "${GREEN}✅ File size check passed${NC}"

# 7. Check for TODO comments (info only)
echo -e "\n${BLUE}7️⃣  Checking for TODO comments...${NC}"
TODO_COUNT=$(git diff --cached app/ tests/ 2>/dev/null | grep -c "^+.*TODO" || echo 0)
if [ $TODO_COUNT -gt 0 ]; then
    echo -e "${YELLOW}💡 Found $TODO_COUNT TODO comment(s) in changes${NC}"
fi

# 8. Final summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✅ All pre-push checks passed!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🚀 Ready to push!${NC}"

exit 0
