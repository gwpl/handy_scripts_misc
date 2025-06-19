# Contributors Guide

## 🔄 **Migrating Tools to Individual Repositories**

When a tool in this repo matures and is ready to move to its own repository under [shibuido](https://github.com/shibuido), follow this migration pattern:

### **Migration Steps:**

1. **Create individual repo** under shibuido organization
2. **Move tool files** to the new repository  
3. **Add as submodule** to this repo with `_repo` suffix
4. **Create symbolic link** for backward compatibility
5. **Document the migration** in commit message

### **Example Migration (tmuxa):**

```bash
# 1. Tool has been moved to https://github.com/shibuido/tmuxa.git
# 2. Add as submodule
git submodule add https://github.com/shibuido/tmuxa.git tmuxa_repo

# 3. Create symbolic link for seamless access
ln -s tmuxa_repo/tmuxa tmuxa

# 4. Commit the migration
git add .
git commit -m "feat: migrate tmuxa to submodule from shibuido

- Add https://github.com/shibuido/tmuxa.git as submodule
- Create symbolic link for backward compatibility
- Tool now has independent development lifecycle

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
```

This pattern ensures:
- ✅ **Backward compatibility** - existing scripts continue to work
- ✅ **Independent development** - tool can evolve in its own repo
- ✅ **Easy access** - users still run `./tmuxa` as before
- ✅ **Clean organization** - each tool has focused development

## 🔗 **Working with Submodules**

This repository uses git submodules to include tools that have graduated to their own repositories under the [shibuido](https://github.com/shibuido) organization. As a contributor, you'll need to understand how to maintain these submodules.

## 📥 **Initial Setup**

When cloning this repository for development:

```bash
git clone --recurse-submodules https://github.com/gwpl/handy_scripts_misc.git
cd handy_scripts_misc
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

## 🔄 **Updating Submodules to Latest HEAD**

### **Update All Submodules to Latest:**

```bash
# Update all submodules to their latest commits on their default branch
git submodule update --remote --merge

# Check what changed
git status
git diff --submodule
```

### **Update Specific Submodule:**

```bash
# Update just one submodule (e.g., ubertmux)
git submodule update --remote --merge ubertmux_repo

# Or manually:
cd ubertmux_repo
git pull origin main  # or master, depending on the repo
cd ..
```

### **Commit Submodule Updates:**

After updating submodules, you need to commit the new gitlink references:

```bash
# Stage the updated submodule references
git add .gitmodules
git add ubertmux_repo  # and any other updated submodules

# Commit with descriptive message
git commit -m "feat: update submodules to latest versions

- ubertmux_repo: Updated to latest HEAD
- Include latest bug fixes and improvements

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to remote
git push origin master
```

## 🚀 **Adding New Submodules**

When a tool graduates from this repo to shibuido:

### **1. Add the Submodule:**

```bash
# Add new submodule
git submodule add https://github.com/shibuido/TOOL_NAME.git TOOL_NAME_repo

# Create symbolic link for backward compatibility
ln -s TOOL_NAME_repo/TOOL_NAME TOOL_NAME
```

### **2. Update Documentation:**

- Add tool to the list in README.md submodules section
- Update any tool-specific READMEs if needed

### **3. Commit Everything:**

```bash
git add .
git commit -m "feat: add TOOL_NAME as submodule from shibuido

- Add https://github.com/shibuido/TOOL_NAME.git as submodule
- Create symbolic link for seamless access
- Maintain backward compatibility for existing users

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin master
```

## 🔍 **Useful Submodule Commands**

### **Check Submodule Status:**

```bash
# See submodule status
git submodule status

# See what commits submodules are pointing to
git submodule foreach 'echo "=== $name ===" && git log --oneline -3'
```

### **Work on Submodule Content:**

```bash
# Enter submodule directory
cd ubertmux_repo

# Make changes, commit, push to its own repo
git add .
git commit -m "fix: your changes"
git push origin main

# Return to main repo and update the reference
cd ..
git add ubertmux_repo
git commit -m "feat: update ubertmux_repo to include latest fixes"
git push origin master
```

### **Sync All Submodules:**

```bash
# One-liner to update everything and commit
git submodule update --remote --merge && \
git add . && \
git commit -m "feat: update all submodules to latest HEAD" && \
git push origin master
```

## 📝 **Best Practices**

1. **Regular Updates**: Update submodules regularly to get latest improvements
2. **Descriptive Commits**: Always describe what changed when updating submodules
3. **Test After Updates**: Verify that updated submodules work correctly
4. **Symbolic Links**: Always maintain symbolic links for backward compatibility
5. **Documentation**: Keep README.md updated when adding/removing submodules

## 🚀 **Quick Update Tool**

For convenience, we provide an automated script to handle the entire submodule update workflow:

### **Using `update-submodules`**

```bash
# Update all submodules and commit gitlinks automatically
./update-submodules

# Preview what would be done without making changes
./update-submodules --dry-run

# Show help and options
./update-submodules --help
```

This script:
- ✅ Updates all submodules to their latest remote HEAD
- ✅ Shows which submodules were updated with before/after SHAs
- ✅ Commits the gitlink changes with a descriptive message
- ✅ Provides clear status and next steps
- ✅ Supports dry-run mode for preview

**Perfect for regular maintenance!** Contributors can run this periodically to keep all submodules current.

## 🎯 **Workflow Summary**

### **Manual Approach:**

```bash
# 1. Update submodules
git submodule update --remote --merge

# 2. Check what changed
git diff --submodule

# 3. Test functionality
./ubertmux --help  # or test other tools

# 4. Commit updates
git add .
git commit -m "feat: update submodules to latest versions"
git push origin master
```

### **Automated Approach:**

```bash
# One command to rule them all
./update-submodules
```

Both approaches keep the repository current with all the latest improvements from the individual tool repositories while maintaining the convenience of the unified access pattern.