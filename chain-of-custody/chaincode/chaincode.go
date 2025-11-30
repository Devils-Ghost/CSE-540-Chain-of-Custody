package main

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// ChainOfCustodyContract provides functions for managing chain of custody
type ChainOfCustodyContract struct {
	contractapi.Contract
}

// Evidence represents an item in the chain of custody
// this is an important structure stored on the ledger (value by key).
type Evidence struct {
	ID          string   `json:"id"`	// primary key, uuid
	Description string   `json:"description"`
	Owner       string   `json:"owner"`
	Location    string   `json:"location"`
	Status      string   `json:"status"`	// e.g-> Collected/Archived/etc.
	CreatedAt   string   `json:"created_at"`
	UpdatedAt   string   `json:"updated_at"`
	Tags        []string `json:"tags"`
}

// CustodyTransfer represents a custody transfer event
type CustodyTransfer struct {
	EvidenceID   string `json:"evidence_id"`
	FromOwner    string `json:"from_owner"`
	ToOwner      string `json:"to_owner"`
	Timestamp    string `json:"timestamp"`
	Reason       string `json:"reason"`
	TransferredBy string `json:"transferred_by"`
}


// InitLedger initializes the ledger with sample data
func (c *ChainOfCustodyContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	evidences := []Evidence{
		{
			ID:          "EV001",
			Description: "Sample Evidence Item",
			Owner:       "Officer Smith",
			Location:    "Evidence Locker A1",
			Status:      "Collected",
			CreatedAt:   time.Now().Format(time.RFC3339),
			UpdatedAt:   time.Now().Format(time.RFC3339),
			Tags:        []string{"sample", "test"},
		},
	}

	for _, evidence := range evidences {
		evidenceJSON, err := json.Marshal(evidence)
		if err != nil {
			return err
		}

		err = ctx.GetStub().PutState(evidence.ID, evidenceJSON)
		if err != nil {
			return fmt.Errorf("failed to put evidence to world state: %v", err)
		}
	}

	return nil
}

func (c *ChainOfCustodyContract) validateNewEvidenceID(ctx contractapi.TransactionContextInterface, id string) error {
    if strings.TrimSpace(id) == "" {
        return fmt.Errorf("evidence id must not be empty")
    }

    exists, err := c.EvidenceExists(ctx, id)
    if err != nil {
        return err
    }
    if exists {
        return fmt.Errorf("evidence %s already exists", id)
    }

    return nil
}

// CreateEvidence creates a new evidence item
// id is unique, owner is required.
func (c *ChainOfCustodyContract) CreateEvidence(ctx contractapi.TransactionContextInterface, id string, description string, owner string, location string, tags []string) error {
    // Validate id before proceeding
    if err := c.validateNewEvidenceID(ctx, id); err != nil {
        return err
    }

    evidence := Evidence{
        ID:          id,
        Description: description,
        Owner:       owner,
        Location:    location,
        Status:      "Collected",
        CreatedAt:   time.Now().Format(time.RFC3339),
        UpdatedAt:   time.Now().Format(time.RFC3339),
        Tags:        tags,
    }

    evidenceJSON, err := json.Marshal(evidence)
    if err != nil {
        return err
    }

    return ctx.GetStub().PutState(id, evidenceJSON)
}

// ReadEvidence retrieves an evidence item by id.
func (c *ChainOfCustodyContract) ReadEvidence(ctx contractapi.TransactionContextInterface, id string) (*Evidence, error) {
	evidenceJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("failed to read evidence: %v", err)
	}
	if evidenceJSON == nil {
		return nil, fmt.Errorf("evidence %s does not exist", id)
	}

	var evidence Evidence
	err = json.Unmarshal(evidenceJSON, &evidence)
	if err != nil {
		return nil, err
	}

	return &evidence, nil
}

// UpdateEvidence updates an existing evidence item
func (c *ChainOfCustodyContract) UpdateEvidence(ctx contractapi.TransactionContextInterface, id string, description string, location string, status string) error {
	evidence, err := c.ReadEvidence(ctx, id)
	if err != nil {
		return err
	}

	evidence.Description = description
	evidence.Location = location
	evidence.Status = status
	evidence.UpdatedAt = time.Now().Format(time.RFC3339)

	evidenceJSON, err := json.Marshal(evidence)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(id, evidenceJSON)
}

// TransferCustody transfers custody to a new owner.
// must verify current ownership and record transfer trail.
func (c *ChainOfCustodyContract) TransferCustody(ctx contractapi.TransactionContextInterface, id string, newOwner string, reason string, transferredBy string) error {
	evidence, err := c.ReadEvidence(ctx, id)
	if err != nil {
		return err
	}

	// Create custody transfer record
	transfer := CustodyTransfer{
		EvidenceID:   id,
		FromOwner:    evidence.Owner,
		ToOwner:      newOwner,
		Timestamp:    time.Now().Format(time.RFC3339),
		Reason:       reason,
		TransferredBy: transferredBy,
	}

	transferJSON, err := json.Marshal(transfer)
	if err != nil {
		return err
	}

	// Store transfer record with composite key
	transferKey := fmt.Sprintf("TRANSFER_%s_%s", id, transfer.Timestamp)
	err = ctx.GetStub().PutState(transferKey, transferJSON)
	if err != nil {
		return err
	}

	// Update evidence owner
	evidence.Owner = newOwner
	evidence.UpdatedAt = time.Now().Format(time.RFC3339)

	evidenceJSON, err := json.Marshal(evidence)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(id, evidenceJSON)
}

// GetEvidenceHistory retrieves the on-ledger history for an evidence id.
func (c *ChainOfCustodyContract) GetEvidenceHistory(ctx contractapi.TransactionContextInterface, id string) ([]map[string]interface{}, error) {
	resultsIterator, err := ctx.GetStub().GetHistoryForKey(id)
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()

	var history []map[string]interface{}

	for resultsIterator.HasNext() {
		response, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}

		var evidence Evidence
		if len(response.Value) > 0 {
			err = json.Unmarshal(response.Value, &evidence)
			if err != nil {
				return nil, err
			}
		}

		record := map[string]interface{}{
			"txId":      response.TxId,
			"timestamp": response.Timestamp,
			"isDelete":  response.IsDelete,
			"evidence":  evidence,
		}

		history = append(history, record)
	}

	return history, nil
}

// GetAllEvidence retrieves all evidence items
func (c *ChainOfCustodyContract) GetAllEvidence(ctx contractapi.TransactionContextInterface) ([]*Evidence, error) {
	resultsIterator, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()

	var evidences []*Evidence

	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}

		var evidence Evidence
		err = json.Unmarshal(queryResponse.Value, &evidence)
		if err != nil {
			continue
		}

		evidences = append(evidences, &evidence)
	}

	return evidences, nil
}

// EvidenceExists checks if a given evidence id exists.
func (c *ChainOfCustodyContract) EvidenceExists(ctx contractapi.TransactionContextInterface, id string) (bool, error) {
	evidenceJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return false, fmt.Errorf("failed to read evidence: %v", err)
	}

	return evidenceJSON != nil, nil
}

// DeleteEvidence deletes an evidence item
func (c *ChainOfCustodyContract) DeleteEvidence(ctx contractapi.TransactionContextInterface, id string) error {
	exists, err := c.EvidenceExists(ctx, id)
	if err != nil {
		return err
	}
	if !exists {
		return fmt.Errorf("evidence %s does not exist", id)
	}

	return ctx.GetStub().DelState(id)
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
