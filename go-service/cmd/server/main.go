package main

import (
	"log"
	"net/http"
	"practical/go-service/internals/handlers"
)

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /flaky-api", handlers.FlakyProcessor)

	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("Healthy"))
	})

	log.Println("go-service started on :8001")

	if err := http.ListenAndServe(":8001", mux); err != nil {
		log.Fatal(err)
	}

}
