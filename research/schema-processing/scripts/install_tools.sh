#!/usr/bin/env bash
# Install benchmark tools for schema-bench
set -euo pipefail

echo "=== Installing benchmark tools ==="

# jq
if command -v jq &>/dev/null; then
    echo "jq: $(jq --version) (already installed)"
else
    echo "Installing jq..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y jq
    elif command -v brew &>/dev/null; then
        brew install jq
    else
        echo "ERROR: Cannot install jq. Install manually."
    fi
fi

# hyperfine
if command -v hyperfine &>/dev/null; then
    echo "hyperfine: $(hyperfine --version) (already installed)"
else
    echo "Installing hyperfine..."
    if command -v cargo &>/dev/null; then
        cargo install hyperfine
    elif command -v apt-get &>/dev/null; then
        sudo apt-get install -y hyperfine
    elif command -v brew &>/dev/null; then
        brew install hyperfine
    else
        echo "ERROR: Cannot install hyperfine. Install via cargo or package manager."
    fi
fi

# gron
if command -v gron &>/dev/null; then
    echo "gron: $(gron --version 2>&1 | head -1) (already installed)"
else
    echo "Installing gron..."
    if command -v brew &>/dev/null; then
        brew install gron
    elif command -v go &>/dev/null; then
        go install github.com/tomnomnom/gron@latest
    else
        echo "WARNING: Cannot install gron. Install manually from https://github.com/tomnomnom/gron"
    fi
fi

# jsongrep (jg)
if command -v jg &>/dev/null; then
    echo "jg: $(jg --version 2>&1 | head -1) (already installed)"
else
    echo "Installing jsongrep..."
    if command -v cargo &>/dev/null; then
        cargo install jsongrep
    else
        echo "ERROR: cargo not found. Install Rust first: https://rustup.rs"
    fi
fi

# jaq
if command -v jaq &>/dev/null; then
    echo "jaq: $(jaq --version 2>&1 | head -1) (already installed)"
else
    echo "Installing jaq..."
    if command -v cargo &>/dev/null; then
        cargo install jaq
    else
        echo "ERROR: cargo not found. Install Rust first."
    fi
fi

echo ""
echo "=== Tool status ==="
for tool in jq jg jaq gron hyperfine; do
    if command -v "$tool" &>/dev/null; then
        echo "  $tool: OK"
    else
        echo "  $tool: MISSING"
    fi
done
