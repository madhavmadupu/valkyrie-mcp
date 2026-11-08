#!/bin/bash

# VALKYRIE - Push to GitHub Script
# Run this after creating your GitHub repository

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║   🚀 VALKYRIE - Push to GitHub                                      ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "src/valkyrie" ]; then
    echo "❌ Error: Not in valkyrie-mcp directory!"
    echo "   Run: cd /c/Users/madha/code/projects/valkyrie-mcp"
    exit 1
fi

echo "✓ In correct directory"
echo ""

# Check if remote already exists
if git remote | grep -q origin; then
    echo "⚠️  Remote 'origin' already exists. Updating URL..."
    git remote set-url origin https://github.com/madhavmadupu/valkyrie-mcp.git
else
    echo "📡 Adding remote 'origin'..."
    git remote add origin https://github.com/madhavmadupu/valkyrie-mcp.git
fi

echo "✓ Remote configured"
echo ""

# Show what we're about to push
echo "📊 Repository Status:"
echo "   Commits: $(git log --oneline | wc -l)"
echo "   Files: $(git ls-files | wc -l)"
echo "   Branch: $(git branch --show-current)"
echo ""

# Confirm push
read -p "🚀 Ready to push to GitHub? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📤 Pushing to GitHub..."
    git branch -M main
    git push -u origin main

    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ SUCCESS! VALKYRIE is now on GitHub!"
        echo ""
        echo "🔗 Repository: https://github.com/madhavmadupu/valkyrie-mcp"
        echo "📖 GitHub Pages: https://madhavmadupu.github.io/valkyrie-mcp (wait 2-3 min)"
        echo ""
        echo "📋 Next Steps:"
        echo "   1. Configure repository (see GITHUB_SETUP.md)"
        echo "   2. Add topics and description"
        echo "   3. Enable GitHub Pages (Settings → Pages)"
        echo "   4. Pin to your profile"
        echo "   5. Launch social media campaign!"
        echo ""
        echo "🎉 Time to make VALKYRIE go viral!"
    else
        echo ""
        echo "❌ Push failed! Check error above."
        echo "   Make sure repository exists: https://github.com/new"
    fi
else
    echo "❌ Push cancelled."
fi
