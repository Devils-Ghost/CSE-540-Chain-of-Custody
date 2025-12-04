#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import re
from typing import List, Dict, Optional
import time
import uuid
import datetime
import base64
import binascii

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
        self.env["CORE_PEER_ADDRESS"] = f"peer0.{self.org_domain}:{self.peer_port}"
        
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
            "-o", "orderer.example.com:7050",
            "--ordererTLSHostnameOverride", "orderer.example.com",
            "--tls", "--cafile", self.orderer_ca,
            "-C", self.channel, "-n", self.chaincode,
            "--peerAddresses", "peer0.org1.example.com:7051", "--tlsRootCertFiles", self.org1_tls_ca,
            "--peerAddresses", "peer0.org2.example.com:9051", "--tlsRootCertFiles", self.org2_tls_ca,
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

    def get_genesis_block(self) -> Dict:
        block_file = os.path.abspath("genesis.block")
        json_file = os.path.abspath("genesis.json")
        
        if os.path.exists(block_file):
            os.remove(block_file)
        if os.path.exists(json_file):
            os.remove(json_file)

        # 1. Fetch Block 0
        cmd_fetch = [
            "peer", "channel", "fetch", "0", block_file,
            "-o", "localhost:7050",
            "--ordererTLSHostnameOverride", "orderer.example.com",
            "--tls", "--cafile", self.orderer_ca,
            "-c", self.channel
        ]
        
        # We suppress output for fetch as it prints to stderr
        self._run_peer_command(cmd_fetch)
        
        if not os.path.exists(block_file):
            return {"timestamp": "Fetch Failed", "hash": "N/A"}

        # 2. Decode with configtxlator
        configtxlator_path = os.path.normpath(os.path.join(self.fabric_path, "../bin/configtxlator"))
        
        if not os.path.exists(configtxlator_path):
             print(f"ERROR: configtxlator not found at {configtxlator_path}")
             return {"timestamp": "Tool Missing", "hash": "N/A"}

        cmd_decode = [
            configtxlator_path, "proto_decode",
            "--input", block_file,
            "--type", "common.Block",
            "--output", json_file
        ]
        
        result = self._run_peer_command(cmd_decode)
        
        if os.path.exists(block_file):
            os.remove(block_file)

        if not result["success"]:
            print(f"ERROR: configtxlator failed: {result.get('error')}")
            if os.path.exists(json_file): os.remove(json_file)
            return {"timestamp": "Decode Failed", "hash": "N/A"}
            
        if not os.path.exists(json_file):
            print("ERROR: configtxlator did not produce output file")
            return {"timestamp": "No Output", "hash": "N/A"}

        try:
            with open(json_file, 'r') as f:
                block_data = json.load(f)
            
            if os.path.exists(json_file):
                os.remove(json_file)
            
            # Extract Timestamp
            # Block -> data -> data[0] -> payload -> header -> channel_header -> timestamp
            try:
                env = block_data['data']['data'][0]
                ts_raw = env['payload']['header']['channel_header']['timestamp']
                
                if isinstance(ts_raw, dict): # Protobuf timestamp dict
                    seconds = int(ts_raw.get('seconds', 0))
                    dt = datetime.datetime.fromtimestamp(seconds)
                    timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                else: # ISO String
                    timestamp = str(ts_raw).replace('T', ' ').split('.')[0]
            except (KeyError, IndexError, ValueError):
                timestamp = "Unknown Format"

            # Extract Data Hash
            header = block_data.get('header', {})
            data_hash_b64 = header.get('data_hash', '')
            
            # Convert Base64 to Hex
            try:
                data_hash_hex = binascii.hexlify(base64.b64decode(data_hash_b64)).decode('utf-8')
            except:
                data_hash_hex = data_hash_b64

            return {
                "timestamp": timestamp,
                "hash": data_hash_hex
            }

        except json.JSONDecodeError:
            if os.path.exists(json_file): os.remove(json_file)
            return {"timestamp": "Parse Error", "hash": "N/A"}
        except Exception as e:
            print(f"Error parsing genesis block: {e}")
            if os.path.exists(json_file): os.remove(json_file)
            return {"timestamp": "Error", "hash": "N/A"}

    def create_evidence(self):
        print(f"\n--- Create New Evidence ({self.friendly_name}) ---")
        #ev_id = input("Evidence ID (e.g. EV001): ").strip()
        ev_id = str(uuid.uuid4())
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
        
        if not isinstance(data, list) or len(data) == 0:
            print("No history found or error.")
            return
        
        print(f"\n{'='*70}")
        print(f"  EVIDENCE HISTORY: {ev_id}")
        print(f"{'='*70}")
        
        # History is in reverse chronological order (newest first)
        for i, item in enumerate(data):
            evidence = item.get('evidence', {})
            is_delete = item.get('isDelete', False)
            ts_raw = item.get('timestamp', {})
            tx_id = item.get('txId', 'N/A')
            
            # Format timestamp
            if isinstance(ts_raw, dict):
                seconds = ts_raw.get('seconds', 0)
                dt = datetime.datetime.fromtimestamp(seconds)
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                formatted_time = str(ts_raw)
            
            # Determine action
            if is_delete:
                action = "DELETED"
            else:
                created_at = evidence.get('created_at', '')
                updated_at = evidence.get('updated_at', '')
                
                if created_at == updated_at:
                    action = "CREATED"
                else:
                    # Check if owner changed compared to previous state (next item in list)
                    current_owner = evidence.get('owner', '')
                    prev_owner = None
                    
                    # Look at the next item (older record) to compare owner
                    if i + 1 < len(data):
                        prev_evidence = data[i + 1].get('evidence', {})
                        prev_owner = prev_evidence.get('owner', '')
                    
                    if prev_owner is not None and current_owner != prev_owner:
                        action = "TRANSFERRED"
                    else:
                        action = "UPDATED"
            
            # Print formatted block
            print(f"\n  ┌{'─'*66}┐")
            print(f"  │ {action:^64} │")
            print(f"  ├{'─'*66}┤")
            print(f"  │ {'Timestamp:':<12} {formatted_time:<52} │")
            print(f"  │ {'TX ID:':<12} {tx_id[:52]:<52} │")
            
            if not is_delete:
                desc = evidence.get('description', 'N/A')
                if len(desc) > 50: desc = desc[:47] + "..."
                owner = evidence.get('owner', 'N/A')
                location = evidence.get('location', 'N/A')
                if len(location) > 50: location = location[:47] + "..."
                status = evidence.get('status', 'N/A')
                tags = evidence.get('tags', [])
                tags_str = ', '.join(tags) if tags else 'None'
                if len(tags_str) > 50: tags_str = tags_str[:47] + "..."
                
                print(f"  ├{'─'*66}┤")
                print(f"  │ {'Owner:':<12} {owner:<52} │")
                print(f"  │ {'Description:':<12} {desc:<52} │")
                print(f"  │ {'Location:':<12} {location:<52} │")
                print(f"  │ {'Status:':<12} {status:<52} │")
                print(f"  │ {'Tags:':<12} {tags_str:<52} │")
            
            print(f"  └{'─'*66}┘")
            
            # Draw arrow to next record (if not last)
            if i < len(data) - 1:
                print(f"{'':^35}▲")
                print(f"{'':^35}│")
        
        print(f"\n{'='*70}")
        print(f"  Total Records: {len(data)}")
        print(f"{'='*70}")

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

    def view_blockchain_ledger(self):
        print(f"\n{'='*70}")
        print(f"  BLOCKCHAIN LEDGER ({self.friendly_name})")
        print(f"{'='*70}")
        print("  Fetching all transactions... this might take a moment...")
        
        # 1. Get all evidence IDs (including deleted ones)
        all_evidence_ids = self.query_chaincode("GetAllEvidenceIDs", [])
        if not all_evidence_ids:
            print("  No evidence found on the ledger.")
            return

        all_txs = []
        
        # 2. For each evidence ID, get its history
        for ev_id in all_evidence_ids:
            if not ev_id: continue
            
            history = self.query_chaincode("GetEvidenceHistory", [ev_id])
            if history:
                for idx, record in enumerate(history):
                    record['asset_id'] = ev_id
                    # Store the previous record's owner for action detection
                    if idx + 1 < len(history):
                        record['prev_owner'] = history[idx + 1].get('evidence', {}).get('owner', '')
                    else:
                        record['prev_owner'] = None
                    all_txs.append(record)
        
        # 3. Sort by timestamp (oldest first for ledger view)
        def get_sort_key(tx):
            ts = tx.get('timestamp')
            if isinstance(ts, dict):
                return ts.get('seconds', 0) + ts.get('nanos', 0) / 1e9
            return ts or ""

        all_txs.sort(key=get_sort_key)

        if not all_txs:
            print("  No transactions found.")
            return

        print(f"\n  Found {len(all_txs)} transactions across {len(all_evidence_ids)} assets.")
        
        # Fetch real genesis block info
        genesis_info = self.get_genesis_block()
        genesis_hash = genesis_info.get('hash', 'N/A')
        
        # If genesis hash failed, use a placeholder
        if genesis_hash == 'N/A':
            genesis_hash = "0" * 56

        # Print Genesis Block
        print(f"\n  ┌{'─'*66}┐")
        print(f"  │ {'GENESIS BLOCK':^64} │")
        print(f"  ├{'─'*66}┤")
        print(f"  │ {'Timestamp:':<12} {genesis_info.get('timestamp', 'N/A'):<52} │")
        print(f"  │ {'Data Hash:':<12} {genesis_hash[:52]:<52} │")
        print(f"  │ {'Prev Hash:':<12} {'0'*52:<52} │")
        print(f"  └{'─'*66}┘")
        
        prev_hash = genesis_hash

        for tx in all_txs:
            tx_id = tx.get('txId', 'N/A')
            ts_raw = tx.get('timestamp', 'N/A')
            
            # Format timestamp
            if isinstance(ts_raw, dict):
                seconds = ts_raw.get('seconds', 0)
                dt = datetime.datetime.fromtimestamp(seconds)
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                formatted_time = str(ts_raw)

            asset_id = tx.get('asset_id', 'N/A')
            is_delete = tx.get('isDelete', False)
            evidence = tx.get('evidence', {})
            prev_owner = tx.get('prev_owner')
            
            # Determine action
            if is_delete:
                action = "DELETED"
            else:
                created_at = evidence.get('created_at', '')
                updated_at = evidence.get('updated_at', '')
                
                if created_at == updated_at:
                    action = "CREATED"
                else:
                    current_owner = evidence.get('owner', '')
                    if prev_owner is not None and current_owner != prev_owner:
                        action = "TRANSFERRED"
                    else:
                        action = "UPDATED"
            
            # Draw link arrow
            print(f"{'':^35}│")
            print(f"{'':^35}▼")
            
            # Print transaction block
            print(f"\n  ┌{'─'*66}┐")
            print(f"  │ {action:^64} │")
            print(f"  ├{'─'*66}┤")
            print(f"  │ {'Timestamp:':<12} {formatted_time:<52} │")
            print(f"  │ {'TX ID:':<12} {tx_id[:52]:<52} │")
            print(f"  │ {'Prev Hash:':<12} {prev_hash[:52]:<52} │")
            print(f"  │ {'Evidence ID:':<12} {asset_id[:52]:<52} │")
            
            if not is_delete:
                desc = evidence.get('description', 'N/A')
                if len(desc) > 50: desc = desc[:47] + "..."
                owner = evidence.get('owner', 'N/A')
                location = evidence.get('location', 'N/A')
                if len(location) > 50: location = location[:47] + "..."
                status = evidence.get('status', 'N/A')
                
                print(f"  ├{'─'*66}┤")
                print(f"  │ {'Owner:':<12} {owner:<52} │")
                print(f"  │ {'Description:':<12} {desc:<52} │")
                print(f"  │ {'Location:':<12} {location:<52} │")
                print(f"  │ {'Status:':<12} {status:<52} │")
            
            print(f"  └{'─'*66}┘")
            
            # Update prev_hash for the next link
            prev_hash = tx_id
        
        print(f"\n{'='*70}")
        print(f"  Total Transactions: {len(all_txs)}")
        print(f"{'='*70}")

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
        print("  8. View Blockchain Ledger")
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
        elif choice == "8": client.view_blockchain_ledger()
        elif choice == "0": sys.exit(0)
        else: print("Invalid choice.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()