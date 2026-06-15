package services

import "time"

type DeliveryConfig struct {
	Timeout           time.Duration
	MaxAttempts       int
	RetryBackoff      time.Duration
	SchedulerInterval time.Duration
}
