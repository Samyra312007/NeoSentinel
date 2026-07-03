# NeoSentinel 3-Node AWS Graviton4 Provisioning

Author: Sahil (Data & Intelligence Plane)  
Audience: Both tracks — required before Week 7 integration  
Last updated: Week 0

This checklist provisions the production demo cluster: **3× AWS Graviton4 (c8g.4xlarge)** running Ubuntu 24.04 ARM64.

---

## Instance Specification

| Property | Value |
| -------- | ----- |
| Instance type | `c8g.4xlarge` (Graviton4, 16 vCPU, 32 GiB RAM) |
| Count | 3 |
| AMI | Ubuntu 24.04 LTS ARM64 (`ubuntu/images/hvm-ssd/ubuntu-noble-24.04-arm64-server-*`) |
| Region | Choose one region and keep all 3 nodes in the same AZ for Redis cluster latency |
| Storage | 100 GiB gp3 root volume per node |
| Node names | `node-001`, `node-002`, `node-003` |

### Node Role Assignment (Week 7)

| Node | Primary role |
| ---- | ------------ |
| node-001 | Dashboard (:8080), agent brain, Traefik ingress, Redis cluster seed |
| node-002 | vLLM worker, Performix daemon, Ray worker |
| node-003 | vLLM worker, Performix daemon, Ray worker |

---

## Security Group

Create one security group `neosentinel-cluster-sg` and attach to all 3 instances.

| Port | Protocol | Source | Service |
| ---- | -------- | ------ | ------- |
| 22 | TCP | Your IP / bastion CIDR | SSH admin |
| 8000 | TCP | `neosentinel-cluster-sg` (self) + your IP | vLLM `/v1/completions`, `/metrics` |
| 8080 | TCP | Your IP | Dashboard (FastAPI + WebSocket) on node-001 |
| 6379 | TCP | `neosentinel-cluster-sg` (self) | Redis client port |
| 7000 | TCP | `neosentinel-cluster-sg` (self) | Redis cluster bus |
| 10001 | TCP | `neosentinel-cluster-sg` (self) | Ray head/worker GCS |

Outbound: allow all (required for apt, Docker pulls, model downloads).

---

## SSH Key Setup

1. Generate a dedicated key pair (do not reuse personal keys):

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/neosentinel-graviton -C "neosentinel-week7"
   ```

2. Import the public key into AWS EC2 → Key Pairs as `neosentinel-graviton`.

3. Launch all 3 instances with this key pair.

4. Add a `~/.ssh/config` block for convenience:

   ```
   Host node-001
       HostName <PUBLIC_IP_NODE_001>
       User ubuntu
       IdentityFile ~/.ssh/neosentinel-graviton

   Host node-002
       HostName <PUBLIC_IP_NODE_002>
       User ubuntu
       IdentityFile ~/.ssh/neosentinel-graviton

   Host node-003
       HostName <PUBLIC_IP_NODE_003>
       User ubuntu
       IdentityFile ~/.ssh/neosentinel-graviton
   ```

5. Verify connectivity from your workstation:

   ```bash
   ssh node-001 "uname -m && lscpu | grep -i sve"
   ssh node-002 "uname -m"
   ssh node-003 "uname -m"
   ```

   Expected: `aarch64` on all nodes; SVE2 support visible on Graviton4.

---

## EC2 Launch Checklist

For each of the 3 instances:

- [ ] Instance type: `c8g.4xlarge`
- [ ] AMI: Ubuntu 24.04 ARM64
- [ ] Key pair: `neosentinel-graviton`
- [ ] Security group: `neosentinel-cluster-sg`
- [ ] Tag `Name`: `node-001` / `node-002` / `node-003`
- [ ] Tag `Project`: `NeoSentinel`
- [ ] Tag `Owner`: `Sahil`
- [ ] Enable detailed monitoring (optional, useful for Week 6 load tests)
- [ ] Assign elastic IP to node-001 if dashboard needs stable public URL

Record private IPs in a cluster inventory file (not committed):

```
node-001  PUBLIC=<ip>  PRIVATE=<ip>
node-002  PUBLIC=<ip>  PRIVATE=<ip>
node-003  PUBLIC=<ip>  PRIVATE=<ip>
```

---

## Post-Launch Bootstrap (Preview — full automation in Week 5 `cluster-init`)

Run on each node after SSH access is confirmed:

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y docker.io docker-compose-v2 git curl
sudo usermod -aG docker ubuntu
```

Verify ARM64 + SVE2:

```bash
grep -m1 'model name' /proc/cpuinfo
grep -E 'sve|sve2' /proc/cpuinfo | head -1
```

---

## Exit Criteria (Week 0)

- [ ] 3× c8g.4xlarge instances running Ubuntu 24.04 ARM64
- [ ] Security group allows ports 22, 8000, 8080, 6379, 7000, 10001
- [ ] SSH key imported and passwordless login works to all 3 nodes
- [ ] Nodes tagged and named `node-001`, `node-002`, `node-003`
- [ ] `ssh node-00X "echo ok"` succeeds for X in 1, 2, 3

---

## Cost Control

- Stop instances when not actively testing (Week 6–7 only need extended uptime).
- Use `simulate` mode locally for daily development — no AWS required until Week 7.
- Estimated cost: ~$0.57/hr per c8g.4xlarge × 3 ≈ $1.71/hr on-demand.

---

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| SSH timeout | Check security group allows port 22 from your current IP |
| Wrong architecture | Re-launch with ARM64 AMI, not x86_64 |
| Redis cluster bus blocked | Ensure port 7000 is open within the security group (self-referencing rule) |
| Ray nodes cannot connect | Open port 10001 between all cluster members |
