BUILD_DIR := build/
BINARY := push-service
GOLANG := go
ENTRYPOINT := ./cmd

.PHONY: build cold-run tidy

build:
	@echo "Building the push-service into the $(BUILD_DIR) directory"
	mkdir -p $(BUILD_DIR)
	$(GOLANG) build -o $(BUILD_DIR)$(BINARY) $(ENTRYPOINT)

cold-run:
	@echo "Running the push-service from the $(BUILD_DIR) directory"
	$(GOLANG) build -o $(BUILD_DIR)$(BINARY) $(ENTRYPOINT) && ./$(BUILD_DIR)$(BINARY)

tidy:
	@echo "Tidying up Golang modules..."
	$(GOLANG) mod tidy
