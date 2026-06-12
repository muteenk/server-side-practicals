package models

type ProcessRequest struct {
	DataID string `json:"data_id"`
}

type ProcessResponse struct {
	DataID string `json:"data_id"`
	Status string `json:"status"`
}
