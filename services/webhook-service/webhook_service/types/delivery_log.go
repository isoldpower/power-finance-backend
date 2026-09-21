package types

import "time"

// DeliveryLogFilters narrow the log.
type DeliveryLogFilters struct {
	Status string
	Event  string
}

// DeliveryAnchor is the keyset position a cursor decodes to.
type DeliveryAnchor struct {
	CreatedAt time.Time
	ID        string
	Backwards bool
}

// DeliveryLogQuery is one page request against the delivery log.
type DeliveryLogQuery struct {
	UserExternalID string
	WebhookID      string
	Filters        DeliveryLogFilters
	Limit          int
	Anchor         *DeliveryAnchor
}

// DeliveryLogPage is one scanned window: Rows holds up to Limit+1, the extra being the lookahead.
type DeliveryLogPage struct {
	Rows  []Delivery
	Total int
}
