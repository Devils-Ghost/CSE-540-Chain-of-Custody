#!/usr/bin/env python3
"""
Chain of Custody CLI Wrapper
A simple Python wrapper that uses subprocess to call Fabric peer CLI commands.
This bypasses the problematic fabric-sdk-py dependency issues.
"""

import subprocess
import json
import os
import time
from typing import List, Dict, Optional

class ChainOfCustodyClient:
    """Client wrapper for Chain of Custody chaincode using peer CLI"""
    
    def __init__(self, fabric_path: str = None):
        """
        Initialize the client
        
        Args:
            fabric_path: Path to fabric-samples/test-network directory
        """
        if fabric_path is None:
            home = os.path.expanduser("~")
            fabric_path = f"{home}/blockchain-projects/fabric-samples/test-network"
        
        self.fabric_path = fabric_path
        self.channel = "mychannel"
        self.chaincode = "chainofcustody"
        
        # Setup environment
        self.env = os.environ.copy()
        self.env["PATH"] = f"{fabric_path}/../bin:{self.env.get('PATH', '')}"
        self.env["FABRIC_CFG_PATH"] = f"{fabric_path}/../config/"
        self.env["CORE_PEER_TLS_ENABLED"] = "true"
        self.env["CORE_PEER_LOCALMSPID"] = "Org1MSP"
        self.env["CORE_PEER_TLS_ROOTCERT_FILE"] = f"{fabric_path}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
        self.env["CORE_PEER_MSPCONFIGPATH"] = f"{fabric_path}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp"
        self.env["CORE_PEER_ADDRESS"] = "localhost:7051"
        
        self.orderer_ca = f"{fabric_path}/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem"
        self.peer_ca = f"{fabric_path}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
    
    def _run_peer_command(self, args: List[str], parse_json: bool = False) -> Dict:
        """Run a peer command and return the result"""
        try:
            result = subprocess.run(
                args,
                env=self.env,
                capture_output=True,
                text=True,
                check=True
            )
            
            if parse_json and result.stdout:
                try:
                    return {"success": True, "data": json.loads(result.stdout)}
                except json.JSONDecodeError:
                    # If JSON parsing fails, return raw output
                    return {"success": True, "data": result.stdout, "raw": True}
            
            return {"success": True, "output": result.stdout, "error": result.stderr}
        
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr or str(e)}
    
    def create_evidence(self, evidence_id: str, description: str, 
                       owner: str, location: str, tags: List[str]) -> Dict:
        """Create a new evidence item"""
        
        tags_json = json.dumps(tags)
        
        args = [
            "peer", "chaincode", "invoke",
            "-o", "localhost:7050",
            "--ordererTLSHostnameOverride", "orderer.example.com",
            "--tls",
            "--cafile", self.orderer_ca,
            "-C", self.channel,
            "-n", self.chaincode,
            "--peerAddresses", "localhost:7051",
            "--tlsRootCertFiles", self.peer_ca,
            "--peerAddresses", "localhost:9051",
            "--tlsRootCertFiles", f"{self.fabric_path}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt",
            "-c", json.dumps({
                "function": "CreateEvidence",
                "Args": [evidence_id, description, owner, location, tags_json]
            })
        ]
        
        result = self._run_peer_command(args)
        if result["success"]:
            print(f"✓ Evidence {evidence_id} created successfully")
            time.sleep(3)  # Wait for transaction to commit
        return result
    
    def read_evidence(self, evidence_id: str) -> Optional[Dict]:
        """Read evidence details"""
        
        args = [
            "peer", "chaincode", "query",
            "-C", self.channel,
            "-n", self.chaincode,
            "-c", json.dumps({
                "function": "ReadEvidence",
                "Args": [evidence_id]
            })
        ]
        
        result = self._run_peer_command(args, parse_json=True)
        
        if result["success"]:
            print(f"✓ Retrieved evidence: {evidence_id}")
            return result["data"]
        else:
            print(f"✗ Failed to read evidence: {result['error']}")
            return None
    
    def update_evidence(self, evidence_id: str, description: str,
                       location: str, status: str) -> Dict:
        """Update evidence details"""
        
        args = [
            "peer", "chaincode", "invoke",
            "-o", "localhost:7050",
            "--ordererTLSHostnameOverride", "orderer.example.com",
            "--tls",
            "--cafile", self.orderer_ca,
            "-C", self.channel,
            "-n", self.chaincode,
            "--peerAddresses", "localhost:7051",
            "--tlsRootCertFiles", self.peer_ca,
            "-c", json.dumps({
                "function": "UpdateEvidence",
                "Args": [evidence_id, description, location, status]
            })
        ]
        
        result = self._run_peer_command(args)
        if result["success"]:
            print(f"✓ Evidence {evidence_id} updated successfully")
            time.sleep(3)  # Wait for transaction to commit
        return result
    
    def transfer_custody(self, evidence_id: str, new_owner: str,
                        reason: str, transferred_by: str) -> Dict:
        """Transfer custody of evidence"""
        
        args = [
            "peer", "chaincode", "invoke",
            "-o", "localhost:7050",
            "--ordererTLSHostnameOverride", "orderer.example.com",
            "--tls",
            "--cafile", self.orderer_ca,
            "-C", self.channel,
            "-n", self.chaincode,
            "--peerAddresses", "localhost:7051",
            "--tlsRootCertFiles", self.peer_ca,
            "-c", json.dumps({
                "function": "TransferCustody",
                "Args": [evidence_id, new_owner, reason, transferred_by]
            })
        ]
        
        result = self._run_peer_command(args)
        if result["success"]:
            print(f"✓ Custody transferred for evidence {evidence_id}")
            time.sleep(3)  # Wait for transaction to commit
        return result
    
    def get_all_evidence(self) -> List[Dict]:
        """Get all evidence items"""
        
        args = [
            "peer", "chaincode", "query",
            "-C", self.channel,
            "-n", self.chaincode,
            "-c", json.dumps({
                "function": "GetAllEvidence",
                "Args": []
            })
        ]
        
        result = self._run_peer_command(args, parse_json=True)
        
        if result["success"]:
            evidence_list = result["data"] or []
            print(f"✓ Retrieved {len(evidence_list)} evidence items")
            return evidence_list
        else:
            print(f"✗ Failed to get evidence: {result['error']}")
            return []
    
    def get_evidence_history(self, evidence_id: str) -> List[Dict]:
        """Get complete history of an evidence item"""
        
        args = [
            "peer", "chaincode", "query",
            "-C", self.channel,
            "-n", self.chaincode,
            "-c", json.dumps({
                "function": "GetEvidenceHistory",
                "Args": [evidence_id]
            })
        ]
        
        result = self._run_peer_command(args, parse_json=True)
        
        if result["success"]:
            if result.get("raw"):
                # Raw output, not JSON - just print it
                print(f"✓ History for evidence {evidence_id}:")
                print(result["data"])
                return []
            else:
                history = result["data"] or []
                print(f"✓ Retrieved history for evidence {evidence_id}")
                return history
        else:
            print(f"✗ Failed to get history: {result['error']}")
            return []
    
    def delete_evidence(self, evidence_id: str) -> Dict:
        """Delete an evidence item"""
        
        args = [
            "peer", "chaincode", "invoke",
            "-o", "localhost:7050",
            "--ordererTLSHostnameOverride", "orderer.example.com",
            "--tls",
            "--cafile", self.orderer_ca,
            "-C", self.channel,
            "-n", self.chaincode,
            "--peerAddresses", "localhost:7051",
            "--tlsRootCertFiles", self.peer_ca,
            "-c", json.dumps({
                "function": "DeleteEvidence",
                "Args": [evidence_id]
            })
        ]
        
        result = self._run_peer_command(args)
        if result["success"]:
            print(f"✓ Evidence {evidence_id} deleted successfully")
            time.sleep(3)  # Wait for transaction to commit
        return result


def main():
    """Demo of the Chain of Custody client"""
    
    print("=" * 60)
    print("CHAIN OF CUSTODY - CLI WRAPPER DEMO")
    print("=" * 60)
    print()
    
    # Initialize client
    client = ChainOfCustodyClient()
    print("[1] Client initialized")
    print()
    
    # Create evidence
    print("[2] Creating evidence...")
    client.create_evidence(
        evidence_id="EV2025-001",
        description="Laptop computer - Dell XPS 15",
        owner="Officer Martinez",
        location="Evidence Room A, Locker 15",
        tags=["electronics", "digital-evidence", "laptop"]
    )
    print()
    
    # Read evidence
    print("[3] Reading evidence...")
    evidence = client.read_evidence("EV2025-001")
    if evidence:
        print(f"    ID: {evidence['id']}")
        print(f"    Description: {evidence['description']}")
        print(f"    Owner: {evidence['owner']}")
        print(f"    Location: {evidence['location']}")
        print(f"    Status: {evidence['status']}")
        print(f"    Tags: {', '.join(evidence['tags'])}")
    print()
    
    # Transfer custody
    print("[4] Transferring custody...")
    client.transfer_custody(
        evidence_id="EV2025-001",
        new_owner="Detective Johnson",
        reason="Forensic analysis required",
        transferred_by="Sergeant Williams"
    )
    print()
    
    # Read updated evidence
    print("[5] Reading updated evidence...")
    evidence = client.read_evidence("EV2025-001")
    if evidence:
        print(f"    New Owner: {evidence['owner']}")
    print()
    
    # Get all evidence
    print("[6] Getting all evidence...")
    all_evidence = client.get_all_evidence()
    for item in all_evidence:
        print(f"    - {item['id']}: {item['description']} (Owner: {item['owner']})")
    print()
    
    # Get history
    print("[7] Getting evidence history...")
    history = client.get_evidence_history("EV2025-001")
    print(f"    Found {len(history)} transaction(s)")
    print()
    
    print("=" * 60)
    print("DEMO COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
