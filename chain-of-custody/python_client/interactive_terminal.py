#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import re
from typing import List, Dict, Optional
import time

ORG_DISPLAY_NAMES = {
    "org1": "Police Department",
    "org2": "Forensics Lab"
}

FABRIC_BASE_PATH = os.path.expanduser("~/blockchain-projects/fabric-samples/test-network")

def get_available_orgs(base_path: str) -> Dict[str, str]:
    orgs_path = os.path.join(base_path, "organizations", "peerOrganizations")
    
    if not os.path.exists(orgs_path):
        return {}

    found_orgs = {}
    for item in os.listdir(orgs_path):
        full_path = os.path.join(orgs_path, item)
        if os.path.isdir(full_path):
            short_name = item.split('.')[0]
            found_orgs[short_name] = item
            
    return found_orgs

def get_available_users(base_path: str, org_domain: str) -> List[str]:
    users_path = os.path.join(base_path, "organizations", "peerOrganizations", org_domain, "users")
    
    if not os.path.exists(users_path):
        return []

    users = []
    for item in os.listdir(users_path):
        full_path = os.path.join(users_path, item)
        if os.path.isdir(full_path):
            username = item.split('@')[0]
            users.append(username)
    
    return sorted(users)


class ChainOfCustodyClient:
    def __init__(self, org_name, org_domain, username):
        self.fabric_path = FABRIC_BASE_PATH
        self.channel = "mychannel"
        self.chaincode = "chainofcustody"
        self.org_name = org_name
        self.org_domain = org_domain
        self.username = username
        
        self.friendly_name = ORG_DISPLAY_NAMES.get(org_name, org_name)

        if "org1" in org_name:
            self.peer_port = "7051"
            self.msp_id = "Org1MSP"
        elif "org2" in org_name:
            self.peer_port = "9051"
            self.msp_id = "Org2MSP"
        else:
            print(f"Warning: Unknown port for {org_name}, defaulting to 7051")
            self.peer_port = "7051"
            self.msp_id = "Org1MSP"

        self.user_msp_dir = f"{self.fabric_path}/organizations/peerOrganizations/{self.org_domain}/users/{self.username}@{self.org_domain}/msp"
        
        if not os.path.exists(self.user_msp_dir):
            raise ValueError(f"MSP directory not found for {username} at {self.user_msp_dir}")

        self.env = os.environ.copy()
        self.env["PATH"] = f"{self.fabric_path}/../bin:{self.env.get('PATH', '')}"
        self.env["FABRIC_CFG_PATH"] = f"{self.fabric_path}/../config/"
        self.env["CORE_PEER_TLS_ENABLED"] = "true"
        self.env["CORE_PEER_LOCALMSPID"] = self.msp_id
        self.env["CORE_PEER_TLS_ROOTCERT_FILE"] = f"{self.fabric_path}/organizations/peerOrganizations/{self.org_domain}/peers/peer0.{self.org_domain}/tls/ca.crt"
        self.env["CORE_PEER_MSPCONFIGPATH"] = self.user_msp_dir
        self.env["CORE_PEER_ADDRESS"] = f"localhost:{self.peer_port}"
        
        self.orderer_ca = f"{self.fabric_path}/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem"
        self.org1_tls_ca = f"{self.fabric_path}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
        self.org2_tls_ca = f"{self.fabric_path}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt"

    def _run_peer_command(self, args: List[str], parse_json: bool = False) -> Dict:
        try:
            result = subprocess.run(
                args, env=self.env, capture_output=True, text=True, check=True
            )
            if parse_json and result.stdout:
                try:
                    return {"success": True, "data": json.loads(result.stdout)}
                except json.JSONDecodeError:
                    return {"success": True, "data": result.stdout, "raw": True}
            return {"success": True, "output": result.stdout, "error": result.stderr}
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr or str(e)
            if "access denied" in err_msg:
                return {"success": False, "error": "ACCESS DENIED: User does not have permission."}
            return {"success": False, "error": err_msg}

    def invoke_transaction(self, function_name: str, args_list: List[str]) -> Dict:
        cmd_args = [
            "peer", "chaincode", "invoke",
            "-o", "localhost:7050",
            "--ordererTLSHostnameOverride", "orderer.example.com",
            "--tls", "--cafile", self.orderer_ca,
            "-C", self.channel, "-n", self.chaincode,
            "--peerAddresses", "localhost:7051", "--tlsRootCertFiles", self.org1_tls_ca,
            "--peerAddresses", "localhost:9051", "--tlsRootCertFiles", self.org2_tls_ca,
            "-c", json.dumps({"function": function_name, "Args": args_list})
        ]
        return self._run_peer_command(cmd_args)

    def query_chaincode(self, function_name: str, args_list: List[str]) -> Optional[Dict]:
        cmd_args = [
            "peer", "chaincode", "query",
            "-C", self.channel, "-n", self.chaincode,
            "-c", json.dumps({"function": function_name, "Args": args_list})
        ]
        result = self._run_peer_command(cmd_args, parse_json=True)
        return result.get("data") if result["success"] else None

    def create_evidence(self):
        print(f"\n--- Create New Evidence ({self.friendly_name}) ---")
        ev_id = input("Evidence ID (e.g. EV001): ").strip()
        desc = input("Description: ").strip()
        owner = input("Initial Owner Name: ").strip()
        loc = input("Location: ").strip()
        tags_input = input("Tags (comma separated): ").strip()
        tags = [t.strip() for t in tags_input.split(",") if t.strip()]
        result = self.invoke_transaction("CreateEvidence", [ev_id, desc, owner, loc, json.dumps(tags)])
        print("Evidence created!" if result["success"] else f"Failed: {result['error']}")

    def read_evidence(self):
        ev_id = input("\nEnter Evidence ID: ").strip()
        data = self.query_chaincode("ReadEvidence", [ev_id])
        if data: print(json.dumps(data, indent=2))
        else: print("Not found or error.")

    def update_evidence(self):
        print(f"\n--- Update Evidence ({self.friendly_name}) ---")
        ev_id = input("ID: ").strip()
        desc = input("New Desc: ").strip()
        loc = input("New Loc: ").strip()
        status = input("New Status: ").strip()
        result = self.invoke_transaction("UpdateEvidence", [ev_id, desc, loc, status])
        print("Updated!" if result["success"] else f"Failed: {result['error']}")

    def transfer_custody(self):
        print(f"\n--- Transfer Custody ({self.friendly_name}) ---")
        ev_id = input("ID: ").strip()
        new_owner = input("New Owner: ").strip()
        reason = input("Reason: ").strip()
        by_whom = input("Transferred By: ").strip()
        result = self.invoke_transaction("TransferCustody", [ev_id, new_owner, reason, by_whom])
        print("Transferred!" if result["success"] else f"Failed: {result['error']}")

    def get_history(self):
        ev_id = input("\nEnter ID for History: ").strip()
        data = self.query_chaincode("GetEvidenceHistory", [ev_id])
        
        if isinstance(data, list):
            for item in data:
                print(json.dumps(item, indent=4))
                print(" "*20 +"A")
                print(" "*20+"|")
                print(" "*20+"|")
        else: print(data)

    def get_all(self):
        data = self.query_chaincode("GetAllEvidence", [])
        if isinstance(data, list):
            for item in data: print(f"[{item.get('id')}] {item.get('description')}")
        else: print("No evidence found.")

    def delete_evidence(self):
        ev_id = input("\n[DANGER] ID to DELETE: ").strip()
        if input(f"Delete {ev_id}? (y/n): ").lower() == 'y':
            result = self.invoke_transaction("DeleteEvidence", [ev_id])
            print("Deleted." if result["success"] else f"Failed: {result['error']}")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    clear_screen()
    print("Welcome to the Secure Evidence Ledger.")

    available_orgs = get_available_orgs(FABRIC_BASE_PATH)
    
    if not available_orgs:
        print("Error: Could not find any organizations.")
        print(f"Checked path: {FABRIC_BASE_PATH}/organizations/peerOrganizations")
        sys.exit(1)

    while True:
        print("\nSelect Organization:")
        org_list = list(available_orgs.keys())
        for i, org in enumerate(org_list):
            display_name = ORG_DISPLAY_NAMES.get(org, org) 
            # print(f"  [{i+1}] {display_name} ({available_orgs[org]})") # If we wanna print the boring org names as well
            print(f"  [{i+1}] {display_name} ")
        
        try:
            choice = input("\nSelect Org Number > ").strip()
            org_idx = int(choice) - 1
            if 0 <= org_idx < len(org_list):
                selected_org_name = org_list[org_idx]
                selected_org_domain = available_orgs[selected_org_name]
                break
            else:
                print("Invalid number.")
        except ValueError:
            print("Please enter a number.")

    while True:
        available_users = get_available_users(FABRIC_BASE_PATH, selected_org_domain)
        
        org_fancy_name = ORG_DISPLAY_NAMES.get(selected_org_name, selected_org_name)
        print(f"\nSelect User for {org_fancy_name}:")
        
        if not available_users:
            print("No users found for this organization.")
            sys.exit(1)

        for i, user in enumerate(available_users):
            print(f"  [{i+1}] {user}")
            
        try:
            choice = input("\nSelect User Number > ").strip()
            user_idx = int(choice) - 1
            if 0 <= user_idx < len(available_users):
                selected_user = available_users[user_idx]
                break
            else:
                print("Invalid number.")
        except ValueError:
            print("Please enter a number.")

    try:
        print(f"\nInitializing client as {selected_user} @ {selected_org_name}...")
        client = ChainOfCustodyClient(selected_org_name, selected_org_domain, selected_user)
        print("Login Successful!")
        time.sleep(1)
    except Exception as e:
        print(f"Error initializing client: {e}")
        sys.exit(1)


    while True:
        clear_screen()
        print("="*60)
        print(f"  USER: {client.username} | ORG: {client.friendly_name.upper()}")
        print("="*60)
        print("  1. Create Evidence")
        print("  2. Read Evidence")
        print("  3. Update Evidence")
        print("  4. Transfer Custody")
        print("  5. History")
        print("  6. Get All")
        print("  7. Delete")
        print("  0. Exit")
        print()
        
        choice = input("Select > ").strip().lower()
        
        if choice == "1": client.create_evidence()
        elif choice == "2": client.read_evidence()
        elif choice == "3": client.update_evidence()
        elif choice == "4": client.transfer_custody()
        elif choice == "5": client.get_history()
        elif choice == "6": client.get_all()
        elif choice == "7": client.delete_evidence()
        elif choice == "0": sys.exit(0)
        else: print("Invalid choice.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()