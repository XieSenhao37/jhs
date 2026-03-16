#!/bin/bash
# apply_patches.sh - Apply Florida patches to frida source with fallback for conflicts
set -e

FRIDA_DIR="$1"
PATCHES_DIR="$2"

if [ -z "$FRIDA_DIR" ] || [ -z "$PATCHES_DIR" ]; then
  echo "Usage: $0 <frida_dir> <patches_dir>"
  exit 1
fi

echo "=== Applying frida-core patches ==="
cd "$FRIDA_DIR/subprojects/frida-core"

for patch in "$PATCHES_DIR/frida-core/"*.patch; do
  patch_name=$(basename "$patch")
  echo "--- Trying patch: $patch_name ---"
  
  if git am --3way "$patch" 2>/dev/null; then
    echo "    [OK] Applied successfully"
  else
    echo "    [WARN] git am failed, trying manual apply..."
    git am --abort 2>/dev/null || true
    
    # Patch 0009: memfd-name-jit-cache
    if echo "$patch_name" | grep -qE "memfd|0009"; then
      echo "    [MANUAL] Applying memfd-name-jit-cache fix..."
      find . -name "*.vala" | xargs grep -l "MEMFD_CREATE" 2>/dev/null | while read f; do
        echo "    Patching $f"
        sed -i 's/Linux\.syscall (LinuxSyscall\.MEMFD_CREATE, name, flags)/Linux.syscall (LinuxSyscall.MEMFD_CREATE, "jit-cache", flags)/g' "$f"
      done
      git add -A && git commit -m "Florida: memfd-name-jit-cache (manual)" --allow-empty
      echo "    [OK] Manual patch applied"
    
    # Patch 0010: exec-anti-anti-frida.py
    elif echo "$patch_name" | grep -qE "anti-anti|0010"; then
      echo "    [MANUAL] Applying exec-anti-anti-frida.py fix..."
      EMBED_AGENT=$(find . -name "embed-agent.py" | head -1)
      if [ -n "$EMBED_AGENT" ]; then
        echo "    Found: $EMBED_AGENT"
        python3 "$PATCHES_DIR/../patch_embed_agent.py" "$EMBED_AGENT"
        git add -A && git commit -m "Florida: exec-anti-anti-frida.py (manual)" --allow-empty
        echo "    [OK] Manual patch applied"
      else
        echo "    [ERROR] embed-agent.py not found!"
        exit 1
      fi
    
    else
      echo "    [ERROR] Unknown failed patch: $patch_name"
      echo "    Trying git apply with fuzzing..."
      if git apply --3way --ignore-whitespace "$patch" 2>/dev/null; then
        git add -A && git commit -m "Florida: $patch_name (fuzzy apply)"
        echo "    [OK] Fuzzy apply succeeded"
      else
        echo "    [FATAL] Cannot apply patch: $patch_name"
        exit 1
      fi
    fi
  fi
done

echo ""
echo "=== Applying frida-gum patches ==="
cd "$FRIDA_DIR/subprojects/frida-gum"

for patch in "$PATCHES_DIR/frida-gum/"*.patch; do
  patch_name=$(basename "$patch")
  echo "--- Trying patch: $patch_name ---"
  
  if git am --3way "$patch" 2>/dev/null; then
    echo "    [OK] Applied successfully"
  else
    echo "    [WARN] git am failed for $patch_name, trying manual apply..."
    git am --abort 2>/dev/null || true
    
    # frida-gum pool-frida: change g_set_prgname("frida") to g_set_prgname("ggbond")
    echo "    [MANUAL] Applying pool-frida fix..."
    find . -name "*.c" | xargs grep -l 'g_set_prgname.*"frida"' 2>/dev/null | while read f; do
      echo "    Patching $f"
      sed -i 's/g_set_prgname ("frida")/g_set_prgname ("ggbond")/g' "$f"
    done
    git add -A && git commit -m "Florida: pool-frida for gum (manual)" --allow-empty
    echo "    [OK] Manual patch applied"
  fi
done

echo ""
echo "=== All patches applied successfully ==="
