# GitHub Repository Configuration

## Repository Settings (copy-paste ready)

### **About Section**
```
Physics-aware mission intelligence for autonomous UAV systems. Enforces aerospace constraints before you build. Stop designing by accident.
```

### **Website**
```
https://madhavmadupu.github.io/valkyrie-mcp
```

### **Topics** (add these one by one)
```
uav
aerospace-engineering
defense-tech
autonomous-systems
artificial-intelligence
mcp
mission-planning
physics-simulation
military
robotics
python
systems-engineering
```

---

## Fixing Git Author Attribution

To ensure only you (madhavmadupu) appear as contributor, run these commands:

```bash
cd /c/Users/madha/code/projects/valkyrie-mcp

# Rewrite git history to change author
git filter-branch --env-filter '
CORRECT_NAME="Madhav Madupu"
CORRECT_EMAIL="your-real-email@example.com"
export GIT_COMMITTER_NAME="$CORRECT_NAME"
export GIT_COMMITTER_EMAIL="$CORRECT_EMAIL"
export GIT_AUTHOR_NAME="$CORRECT_NAME"
export GIT_AUTHOR_EMAIL="$CORRECT_EMAIL"
' --tag-name-filter cat -- --branches --tags

# Force push (only do this BEFORE anyone else clones)
git push origin main --force
```

**Alternative (Cleaner):** If you haven't pushed yet:

```bash
cd /c/Users/madha/code/projects/valkyrie-mcp

# Check current author
git log --format='%an <%ae>'

# If it shows wrong email, amend all commits
git rebase -i --root

# In the editor that opens, change all "pick" to "edit"
# Then for each commit:
git commit --amend --author="Madhav Madupu <your-email@example.com>" --no-edit
git rebase --continue
```

**Easiest Option:** Just keep Co-Authored-By in commit messages (standard practice):
- Primary author: You
- Co-author: Claude
- This is transparent and professional!

---

## GitHub Pages Setup

### Enable GitHub Pages:
1. Go to: `Settings` → `Pages`
2. **Source**: Deploy from a branch
3. **Branch**: `main`
4. **Folder**: `/docs`
5. **Click**: Save

### Wait 2-3 minutes, then visit:
```
https://madhavmadupu.github.io/valkyrie-mcp
```

---

## Repository Description & Social Preview

### Short Description (for searches):
```
VALKYRIE: Physics-aware mission intelligence for UAV design. Enforce aerospace constraints before you build.
```

### Social Preview Image (Optional - create later):
- Dimensions: 1280x640px
- Shows: VALKYRIE logo + tagline
- Upload at: Settings → General → Social preview

---

## Pin to Profile

1. Go to your profile: `https://github.com/madhavmadupu`
2. Click: "Customize your pins"
3. Select: `valkyrie-mcp`
4. Click: "Save pins"

---

## Removing "Co-Authored-By" from GitHub UI

GitHub shows contributors based on commit **authors**, not Co-Authored-By tags.

If commits are authored with your email, only you appear as contributor.

**To check:**
```bash
git log --format='%an <%ae>'
```

**If it shows "claude@..." as author:**
You need to rewrite history before first push (commands above).

**If it shows your email:**
You're good! Co-Authored-By is just metadata and won't show @claude in contributors.

---

## Ready to Push Checklist

- [ ] Git history shows your email as author
- [ ] docs/index.html exists
- [ ] README.md is professional
- [ ] .gitignore includes common Python patterns
- [ ] All tests passing (or acceptable failures documented)
- [ ] CONTRIBUTING.md exists
- [ ] LICENSE exists

If all checked, you're ready to:

```bash
git remote add origin https://github.com/madhavmadupu/valkyrie-mcp.git
git push -u origin main
```

Then configure repository as described above.
