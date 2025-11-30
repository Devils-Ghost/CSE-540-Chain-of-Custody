# Chain of Custody - Hyperledger Fabric Project

## Introduction

A blockchain-based chain of custody system built with Hyperledger Fabric and Python. This system provides an immutable record of evidence handling, ensuring transparency and accountability in custody transfers.

The project addresses the limitations of the traditional chain of custody processes, like manual handling, tampering risks and lack of transparency, by developing a blockchain-based framework for secure, verifiable, and tamperproof digital evidence management. Designed for law enforcement and judiciary stakeholders, the system will enhance evidence integrity, traceability, and accountability throughout its lifecycle while tackling challenges in authentication, privacy, interoperability, and legal compliance to strengthen the reliability of judicial proceedings.

## Key Features

### Chaincode Functions
- CreateEvidence - Register new evidence
- ReadEvidence - Query evidence details
- UpdateEvidence - Modify evidence information
- TransferCustody - Change ownership with audit trail
- GetEvidenceHistory - Complete transaction history
- GetAllEvidence - List all evidence items
- DeleteEvidence - Remove evidence (audit trail preserved)

## Use Cases

This system is perfect for:
- **Law Enforcement** - Evidence management
- **Healthcare** - Sample tracking
- **Supply Chain** - Product authentication
- **Legal** - Document chain of custody
- **Research** - Lab sample tracking
- **Compliance** - Audit trail requirements

## Project Structure

```
chain-of-custody/
├── chaincode/
│   └── chaincode.go          # Hyperledger Fabric chaincode (smart contract)
└── python_client/
    └── chain_of_custody_client.py  # Python client
```

## Technology Stack

- **Blockchain**: Hyperledger Fabric 2.x
- **Smart Contract**: Go 1.20+
- **Client**: Python 3.8+
- **SDK**: fabric-sdk-py
- **Container**: Docker & Docker Compose

## Pre-Setup Checklist

### System Requirements

```
Operating System:
□ macOS 11+ / Windows 10+ with WSL2
□ Minimum 8GB RAM
□ Minimum 20GB free disk space

User Permissions:
□ Sudo/admin access (for installations)
□ Ability to run Docker without sudo
```

---
## Phase 1: Install Prerequisites

### 1.1 Docker & Docker Compose

**macOS:**
```bash
□ Download Docker Desktop from docker.com
□ Install Docker Desktop
□ Start Docker Desktop
□ Verify: docker --version
□ Test: docker run hello-world
```

**Windows:**
```bash
□ Install WSL2
□ Install Docker Desktop with WSL2 backend
□ Verify: docker --version (in WSL2 terminal)
```

**Verification Command:**
```bash
docker --version && docker compose version && docker run hello-world
```

**Success**: Should see version numbers and "Hello from Docker!"

---

### 1.2 Go Programming Language

```bash
□ Linux(WSL2): wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
□ Linux(WSL2): sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
□ macOS: brew install go
□ Add to PATH: export PATH=$PATH:/usr/local/go/bin
□ Add to ~/.bashrc or ~/.zshrc for persistence
□ Verify: go version
```

**Expected Output:**
```
go version go1.21.5 linux/amd64
```

**Success**: Go version 1.20 or higher

---

### 1.3 Python 3.8+

```bash
□ Linux(WSL2): sudo apt-get install -y python3 python3-pip python3-venv
□ macOS: brew install python3
□ Verify: python3 --version
□ Verify: pip3 --version
```

**Expected Output:**
```
Python 3.8+ (or higher)
pip 20+ (or higher)
```

**Success**: Python 3.8+ installed

---

### 1.4 Git

```bash
□ Linux(WSL2): sudo apt-get install -y git
□ macOS: brew install git
□ Verify: git --version
```

---

### 1.5 Prerequisites Verification

Run this preqrequisite check script:

```bash
#!/bin/bash
echo "=== Prerequisites Check ==="
echo ""

check_command() {
    if command -v $1 &> /dev/null; then
        echo "Success $1: $($1 --version 2>/dev/null || $1 version | head -1)"
    else
        echo "Errorrrrrr!!!!!!!! $1 is not working!!"
    fi
}

check_command docker
check_command docker-compose
check_command go
check_command python3
check_command pip3
check_command git

echo ""
echo "=== Docker Test ==="
docker run --rm hello-world 2>&1 | grep "Hello from Docker" && echo "Success Docker working" || echo "Errorrrrrr!!!!!!!! Docker is not working!!"
```

**All items should show Success**

---

## Phase 2: Hyperledger Fabric Test Network Setup

### 2.1 Create Project Directory

```bash
□ Run: mkdir -p ~/blockchain-projects
□ Run: cd ~/blockchain-projects
□ Verify: pwd
   Should show: /home/YOUR_USERNAME/blockchain-projects
```

---

### 2.2 Download Fabric Samples

```bash
□ Run: curl -sSL https://raw.githubusercontent.com/hyperledger/fabric/release-2.2/scripts/bootstrap.sh | bash -s -- 2.5.0 1.5.5
□ Wait for download to complete
□ Verify: ls fabric-samples
   Should see: bin/ config/ test-network/ chaincode/ etc.
```

**What this downloads:**
- Fabric binaries (peer, orderer, configtxgen, etc.)
- Docker images (peer, orderer, CA)
- Sample projects and configurations
- Test network

**Success**: Directory `fabric-samples` exists with subdirectories

---

### 2.3 Verify Fabric Binaries

```bash
□ Run: cd ~/blockchain-projects/fabric-samples
□ Run: export PATH=${PWD}/bin:$PATH
□ Run: peer version
   Should show Fabric peer version
□ Run: orderer version
   Should show Fabric orderer version
```

---
### 2.4 Start the Hyperledger Fabric Test Network
```bash
./network.sh up createChannel -c mychannel -ca
```
---

## Project start:
- Copy chain-of-custody to fabric-samples/chaincode
- cd ~/blockchain-projects/fabric-samples/test-network
- ./network.sh up createChannel -c mychannel -ca

- ./network.sh deployCC \
  -ccn chainofcustody \
  -ccp ../chaincode/chain-of-custody/chaincode \
  -ccl go

- cd ~/blockchain-projects/fabric-samples/chaincode/chain-of-custody/python_client
- ./interactive_terminal.py