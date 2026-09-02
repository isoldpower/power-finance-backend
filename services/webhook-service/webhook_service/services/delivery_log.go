package services

import (
	"context"
	"errors"

	"services/webhook-service/webhook_service/types"
)

// ErrWebhookNotFound is returned when the endpoint is neither one the caller
// owns nor one they ever had deliveries for.
var ErrWebhookNotFound = errors.New("delivery log: webhook not found")

type deliveryLogStore interface {
	HasDeliveries(ctx context.Context, userExternalID, webhookID string) (bool, error)
	Count(ctx context.Context, query types.DeliveryLogQuery) (int, error)
	List(ctx context.Context, query types.DeliveryLogQuery) ([]types.Delivery, error)
}

type endpointOwnerResolver interface {
	EndpointOwner(ctx context.Context, webhookID string) (string, error)
}

type DeliveryLogService struct {
	log       deliveryLogStore
	endpoints endpointOwnerResolver
}

func NewDeliveryLogService(log deliveryLogStore, endpoints endpointOwnerResolver) *DeliveryLogService {
	return &DeliveryLogService{log: log, endpoints: endpoints}
}

// List answers the delivery log for one endpoint, refusing endpoints the caller
// has no claim on.
func (s *DeliveryLogService) List(
	ctx context.Context,
	query types.DeliveryLogQuery,
) (types.DeliveryLogPage, error) {
	owned, ownershipErr := s.owns(ctx, query.UserExternalID, query.WebhookID)
	if ownershipErr != nil {
		return types.DeliveryLogPage{}, ownershipErr
	}
	if !owned {
		return types.DeliveryLogPage{}, ErrWebhookNotFound
	}

	total, countErr := s.log.Count(ctx, query)
	if countErr != nil {
		return types.DeliveryLogPage{}, countErr
	}

	rows, listErr := s.log.List(ctx, query)
	if listErr != nil {
		return types.DeliveryLogPage{}, listErr
	}

	return types.DeliveryLogPage{Rows: rows, Total: total}, nil
}

// owns accepts either a live endpoint the caller registered or a log they
// already have rows in — deleting a webhook must not delete its history.
func (s *DeliveryLogService) owns(ctx context.Context, userExternalID, webhookID string) (bool, error) {
	owner, ownerErr := s.endpoints.EndpointOwner(ctx, webhookID)
	if ownerErr != nil {
		return false, ownerErr
	}
	if owner != "" {
		return owner == userExternalID, nil
	}

	return s.log.HasDeliveries(ctx, userExternalID, webhookID)
}
