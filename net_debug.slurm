#!/bin/bash
#SBATCH --job-name=net_debug
#SBATCH --output=net_debug.out
#SBATCH --time=00:05:00

echo "=== Compute Node Network Info ==="
echo "Hostname: $(hostname)"
echo "IP Addresses:"
ip addr show

echo ""
echo "=== Connectivity Check ==="
# Try to ping the login node's likely internal IPs (guessing common subnets)
# Replace these with the actual Login Node internal IP if known.
# Often login nodes are named 'login01', 'login1', etc.

echo "Pinging login node (hostname):"
ping -c 3 login01 || echo "Could not ping 'login01'"
ping -c 3 login1 || echo "Could not ping 'login1'"

echo ""
echo "=== Route Table ==="
ip route

echo ""
echo "=== Testing Connection to Login Node Port 13579 (if Master is there) ==="
# Assuming Login Node might be at a specific IP found in 'ip route' default gateway or similar.
# This is just a blind check.
