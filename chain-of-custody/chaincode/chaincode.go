package main

import (
  "encoding/json"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// ChainOfCustodyContract provides functions for managing chain of custody.
type ChainOfCustodyContract struct {
	contractapi.Contract
}

// evidence represents an item in the chain of custody.
// this is an important structure stored on the ledger (value by key).
type Evidence struct {
	ID    string `json:"id"`    // primary key, uuid
	Owner string `json:"owner"`
	Description string `json:"description"`
	Location    string `json:"location"`
	Status      string `json:"status"` // e.g-> Collected/Archived/etc.
	CreatedAt   string `json:"created_at"`
	UpdatedAt   string `json:"updated_at"`
	Tags        []string `json:"tags"`
	Hash        string `json:"hash"` // integrity of the underlying blob
	// TODO: add more fields (iterate as schema stabilizes)
}

// CustodyTransfer represents a custody transfer event.
type CustodyTransfer struct {
	EvidenceID string `json:"evidence_id"`
	FromOwner  string `json:"from_owner"`
	ToOwner    string `json:"to_owner"`
	Reason       string `json:"reason"`
	TransferredBy string `json:"transferred_by"`
	Timestamp     string `json:"timestamp"`
	// TODO: extend fields
}

// InitLedger initializes the ledger with sample data.
func (c *ChainOfCustodyContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	// TODO:
	// - consider guarding with a config flag or env var.
	return nil
}

// CreateEvidence creates a new evidence item.
// id is unique, owner is required.
func (c *ChainOfCustodyContract) CreateEvidence(
	ctx contractapi.TransactionContextInterface, // this is provided by hyperledger api
	id string,
	description string,
	owner string,
	location string,
	tags []string,
) error {
	// TODO:
	// - validate inputs (non-empty id/owner, length constraints).
	// - check existence using EvidenceExists.
	// - build Evidence struct (set timestamps/status).
	return nil
}

// ReadEvidence retrieves an evidence item by id.
func (c *ChainOfCustodyContract) ReadEvidence(
	ctx contractapi.TransactionContextInterface,
	id string,
) (*Evidence, error) {
	// TODO:
	// - GetState(id); if nil -> return not found
	return nil, nil
}

// UpdateEvidence updates mutable fields on an existing evidence item.
func (c *ChainOfCustodyContract) UpdateEvidence(
	ctx contractapi.TransactionContextInterface,
	id string,
	description string,
	location string,
	status string,
) error {
	// TODO:
	// - only current owner or privileged role may update
	// - read existing record; apply partial updates
	return nil
}

// TransferCustody transfers custody to a new owner.
// must verify current ownership and record transfer trail.
func (c *ChainOfCustodyContract) TransferCustody(
	ctx contractapi.TransactionContextInterface,
	id string,
	newOwner string,
	reason string,
	transferredBy string,
) error {
	// TODO:
	// - permission check (owner/role)
	// - read evidence, verify FromOwner
	// - create CustodyTransfer record (can consider the usage of a composite key-> "transfer:"+id+":"+timestamp)
	return nil
}

// GetEvidenceHistory retrieves the on-ledger history for an evidence id.
func (c *ChainOfCustodyContract) GetEvidenceHistory(
	ctx contractapi.TransactionContextInterface,
	id string,
) ([]map[string]interface{}, error) {
	// TODO:
	// - use stub.GetHistoryForKey(id)
	// - iterate results, decode values into evidence when present
	return nil, nil
}

// GetAllEvidence retrieves all evidence items.
func (c *ChainOfCustodyContract) GetAllEvidence(
	ctx contractapi.TransactionContextInterface,
) ([]*Evidence, error) {
	// TODO:
	// - use GetStateByRange (suggestion: try something like key prefixing)
	// - iterate, deserialize, append
	// - brainstorm this idea add pagination 
	return nil, nil
}

// EvidenceExists checks if a given evidence id exists.
func (c *ChainOfCustodyContract) EvidenceExists(
	ctx contractapi.TransactionContextInterface,
	id string,
) (bool, error) {
	// minimal implementation (kept tiny so code compiles & is useful now)
	bz, err := ctx.GetStub().GetState(id)
	if err != nil {
		return false, fmt.Errorf("read state: %w", err)
	}
	return bz != nil, nil
}

// DeleteEvidence deletes an evidence item.
func (c *ChainOfCustodyContract) DeleteEvidence(
	ctx contractapi.TransactionContextInterface,
	id string,
) error {
	// TODO:
	// avoid hard delete, do something like status=Archived, need to check if archives can be a new function later.
	return nil
}

// main starts the chaincode process.
func main() {
	chaincode, err := contractapi.NewChaincode(&ChainOfCustodyContract{})
	if err != nil {
		fmt.Printf("Error creating chain of custody chaincode: %v\n", err)
		return
	}
	if err := chaincode.Start(); err != nil {
		fmt.Printf("Error starting chain of custody chaincode: %v\n", err)
	}
}



