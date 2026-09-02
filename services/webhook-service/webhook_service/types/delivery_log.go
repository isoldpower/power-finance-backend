package types

import "time"

// DeliveryLogFilters narrow the log. A blank value means "no restriction",
// matching the API's rule that an absent filter is not a default.
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

type DeliveryLogQuery struct {
	UserExternalID string
	WebhookID      string
	Filters        DeliveryLogFilters
	Limit          int
	Anchor         *DeliveryAnchor
}

// DeliveryLogPage is one scanned window: `Rows` holds up to Limit+1 rows so the
// caller can tell whether another page exists without a second query.
type DeliveryLogPage struct {
	Rows  []Delivery
	Total int
}
