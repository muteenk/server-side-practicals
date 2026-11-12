package handlers

import (
	"encoding/json"
	"log"
	"math/rand/v2"
	"net/http"
	"practical/go-service/internals/models"
	"time"
)

func FlakyProcessor(w http.ResponseWriter, r *http.Request) {
	var req models.ProcessRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid Request", http.StatusBadRequest)
		return
	}

	log.Printf("processing data: %s", req.DataID)

	delay := rand.IntN(5)
	time.Sleep(time.Duration(delay) * time.Second)

	if rand.IntN(100) < 20 {
		http.Error(
			w,
			"processing failed",
			http.StatusBadGateway,
		)
		return
	}

	response := models.ProcessResponse{
		DataID: req.DataID,
		Status: "processed",
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(response); err != nil {
		http.Error(w, "Failed to encode response", http.StatusInternalServerError)
	}

}
