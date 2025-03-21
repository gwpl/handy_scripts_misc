#!/bin/bash

echo "Initialising Git aliases and other globals"

# Set git color auto
git config --global color.branch auto
git config --global color.diff auto
git config --global color.interactive auto
git config --global color.status auto
git config --global color.grep auto

# Primary aliases
git config --global alias.ci 'commit'
git config --global alias.staged 'diff --staged'
git config --global alias.joke-staged '!f() { if [ -z "$(git diff --cached)" ]; then echo "No changes to be committed. Please \`git add\` changes to make this work."; else git diff --cached | mods --no-cache -m gpt-4o -qr "Make short nerdy joke about changes you see."; fi; }; f'
git config --global alias.joke-staged-old '!f() { git diff --cached | mods --no-cache -m gpt-4o -qr "Make short nerdy joke about changes you see. If none just say : Please \`git add\` changes for me to see."; }; f'
git config --global alias.joke 'joke-staged'
git config --global alias.critic-staged '!f() { if [ -z "$(git diff --cached)" ]; then echo "No changes to be committed. Please \`git add\` changes to make this work."; else git diff --cached | mods --no-cache -m gpt-4o -qr "You are \`git diff --staged\` changes reviewer. Focus on changes made by user only, and provide concise response. When making sanity check, instead of rewriting all changes that user made, focus on things that you are concerened about, and WHY. Start with your WHY. Be brutally honest critic of changes to be introduced. User is about to commit those staged changes and is asking you for brutally honest opinion. Assume high readability and technically sophisticated reader. Levarage jardon and terminology of the domain, to minimize amount of words and maximize amount of information conveyed in structured way. Use multiple multi level lists formatting paragraphs metaphores, code snippets, mix language with code, to be maximally information efficient and concise."; fi; }; f'
git config --global alias.critic 'critic-staged'
git config --global alias.crit 'critic'
git config --global alias.sanity-check-staged '!f() { if [ -z "$(git diff --cached)" ]; then echo "No changes to be committed. Please \`git add\` changes to make this work."; else git diff --cached | mods --no-cache -m gpt-4o -qr "You are \`git diff --staged\` changes reviewer. Focus on changes made by user only, and provide concise response. When making sanity check, instead of rewriting all changes that user made, focus on things that you are concerened about, and WHY. Start with your WHY. Therefore, Sanity check of changes to be introduced. User is about to commit those staged changes and is asking you for sanity check (pay attention at all possible security and reliability inplications of changes that are considered to be done). Assume high readability and technically sophisticated reader. Levarage jardon and terminology of the domain, to minimize amount of words and maximize amount of information conveyed in structured way. Use multiple multi level lists formatting paragraphs metaphores, code snippets, mix language with code, to be maximally information efficient and concise."; fi; }; f'
git config --global alias.sanity-check 'sanity-check-staged'
git config --global alias.sc 'sanity-check'
git config --global alias.cm '!f() { git diff --cached | mods --no-cache -m gpt-4o -qr "Make commit message for provided diff. Write only commit message, starting with first line summary (following conventional commits standard), then followed with concise information dense summary, levaraging on the fact that reader is highly technical sophisticated expert. Make rest very concise, information dense, maximum information, and minimization of words, utilize bullet lists (and for bullets use asterix * symbol)."; }; f'
git config --global alias.cim '!sh -c "git commit -v -e -F <(git cm)"'

# Common quick aliases
git config --global alias.st 'status'
git config --global alias.br 'branch'
git config --global alias.co 'checkout'
git config --global alias.a 'add'
git config --global alias.d 'diff'
git config --global alias.m 'merge --no-ff'
git config --global alias.noff 'merge --no-ff'
git config --global alias.noffnc 'merge --no-ff --no-commit'
git config --global alias.wdiff 'diff --color-words'
git config --global alias.gn 'grep -n'
git config --global alias.logol 'log --pretty=oneline'
git config --global alias.logg 'log --graph --oneline --decorate'

# Diff tool aliases
git config --global alias.vimdiff 'difftool --tool=vimdiff'
git config --global alias.nvimdiff '!f() { git difftool -t nvimdiff ${1:-HEAD^}; }; f'
git config --global alias.meld 'difftool --tool=meld'
git config --global alias.kdiff3 'difftool --tool=kdiff3'
git config --global alias.beyondcompare 'difftool --tool=bcomp'
git config --global alias.diffmerge 'difftool --tool=diffmerge'
git config --global alias.p4merge 'difftool --tool=p4merge'
git config --global alias.kompare 'difftool --tool=kompare'
git config --global alias.gvimdiff 'difftool --tool=gvimdiff'
git config --global alias.ldiff 'difftool -t latex'

# Other utility aliases
git config --global alias.pullup '!git pull && git submodule update --recursive --remote'
git config --global alias.toplevel 'rev-parse --show-toplevel'
git config --global alias.HEAD 'rev-parse HEAD'

# Diff and Merge config
git config --global diff.tool nvimdiff
git config --global difftool.prompt false
git config --global difftool.nvimdiff.cmd 'nvim -d "$LOCAL" "$REMOTE"'

# User configuration (example)
git config --global user.email "user@localhost"
git config --global user.name "LocalhostUser"

# Credential helper
git config --global credential.helper 'cache --timeout=3600'

# Default branch name
git config --global init.defaultBranch master

# Merge and Pull configs
git config --global merge.ff only
git config --global pull.ff only

echo "Git aliases and configurations are initialized!"
