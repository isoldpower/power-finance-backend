package consumer

import (
	"errors"
	"math"
	"math/rand/v2"
	"time"

	kafkaclient "github.com/power-finance/kafka-client-go"
)

type RetryPolicy struct {
	MaxInProcessAttempts  int
	MaxRetryTopicAttempts int

	InitialBackoff    time.Duration
	MaxBackoff        time.Duration
	BackoffMultiplier float64
	JitterRatio       float64

	Retryable     []error
	RetryableFunc func(error) bool
}

func DefaultRetryPolicy() RetryPolicy {
	return RetryPolicy{
		MaxInProcessAttempts:  3,
		MaxRetryTopicAttempts: 5,
		InitialBackoff:        time.Second,
		MaxBackoff:            10 * time.Minute,
		BackoffMultiplier:     2.0,
		JitterRatio:           0.2,
	}
}

func (p RetryPolicy) IsRetryable(err error) bool {
	if errors.Is(err, kafkaclient.ErrPoison) {
		return false
	} else if errors.Is(err, kafkaclient.ErrTransient) {
		return true
	}

	for _, target := range p.Retryable {
		if errors.Is(err, target) {
			return true
		}
	}

	return p.RetryableFunc != nil && p.RetryableFunc(err)
}

func (p RetryPolicy) ComputeBackoff(retryTopicAttempt int) time.Duration {
	if retryTopicAttempt < 1 {
		retryTopicAttempt = 1
	}

	baseSeconds := p.InitialBackoff.Seconds() * math.Pow(
		p.BackoffMultiplier,
		float64(retryTopicAttempt-1),
	)
	cappedSeconds := math.Min(baseSeconds, p.MaxBackoff.Seconds())

	if p.JitterRatio > 0 {
		jitterSpread := cappedSeconds * p.JitterRatio
		cappedSeconds += (rand.Float64()*2 - 1) * jitterSpread
		cappedSeconds = math.Max(cappedSeconds, 0.0)
	}

	return time.Duration(cappedSeconds * float64(time.Second))
}

func (p RetryPolicy) ComputeRetryAt(retryTopicAttempt int, now time.Time) time.Time {
	if now.IsZero() {
		now = time.Now().UTC()
	}
	return now.Add(p.ComputeBackoff(retryTopicAttempt))
}
