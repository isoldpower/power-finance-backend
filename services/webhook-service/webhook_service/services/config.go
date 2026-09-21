package services

import "time"

// DeliveryConfig is the retry policy the attempter and scheduler share.
type DeliveryConfig struct {
	Timeout           time.Duration
	MaxAttempts       int
	RetryBackoff      time.Duration
	SchedulerInterval time.Duration
}
