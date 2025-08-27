#!/bin/bash
# 🔥 SYSTEM MEMORY OPTIMIZATION FOR AI PROCESSES

echo "🔥 Optimizing system memory for AI processes..."

# Increase swap usage threshold
echo 10 | sudo tee /proc/sys/vm/swappiness

# Optimize memory overcommit
echo 1 | sudo tee /proc/sys/vm/overcommit_memory

# Clear system caches
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches

# Set memory limits for AI processes
ulimit -v 2097152  # 2GB virtual memory limit per process

echo "✅ System memory optimization complete"
echo "📊 Available memory:"
free -h
