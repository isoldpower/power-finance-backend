package demotraces

import (
	"bytes"
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"slices"
	"strings"
)

//go:embed span_narratives.json
var spanNarrativesDocument []byte

const (
	attributePlaceholderPrefix     = "attr:"
	attributeAlternativesSeparator = "|"
	failedSpanNarrativeSuffix      = " It failed."
	failedSpanStatus               = "error"
	millisecondsPerSecond          = 1000
)

var narrativePlaceholderPattern = regexp.MustCompile(`\{([^{}]+)\}`)

var alwaysAvailablePlaceholders = []string{"service", "name", "kind", "duration"}

var knownPlaceholders = append(slices.Clone(alwaysAvailablePlaceholders), "nameRemainder")

type narrativeMatch struct {
	Services   []string          `json:"services"`
	Kind       string            `json:"kind"`
	Names      []string          `json:"names"`
	NamePrefix string            `json:"namePrefix"`
	NameSuffix string            `json:"nameSuffix"`
	Attributes map[string]string `json:"attributes"`
}

type narrativeRule struct {
	Match    narrativeMatch `json:"match"`
	Template string         `json:"template"`
}

type narrativesDocument struct {
	Version int             `json:"version"`
	Rules   []narrativeRule `json:"rules"`
}

type SpanNarrator struct {
	rules []narrativeRule
}

func NewSpanNarrator() (*SpanNarrator, error) {
	return parseSpanNarrator(spanNarrativesDocument)
}

func parseSpanNarrator(document []byte) (*SpanNarrator, error) {
	decoder := json.NewDecoder(bytes.NewReader(document))
	decoder.DisallowUnknownFields()

	var decodedDocument narrativesDocument
	if decodeErr := decoder.Decode(&decodedDocument); decodeErr != nil {
		return nil, fmt.Errorf("span narratives: decode: %w", decodeErr)
	}
	if validationErr := validateNarrativeRules(decodedDocument.Rules); validationErr != nil {
		return nil, fmt.Errorf("span narratives: %w", validationErr)
	}

	return &SpanNarrator{rules: decodedDocument.Rules}, nil
}

func validateNarrativeRules(rules []narrativeRule) error {
	if len(rules) == 0 {
		return errors.New("no rules declared")
	}

	for ruleIndex, rule := range rules {
		if strings.TrimSpace(rule.Template) == "" {
			return fmt.Errorf("rule %d has an empty template", ruleIndex)
		}
		for _, placeholder := range templatePlaceholders(rule.Template) {
			if !isKnownPlaceholder(placeholder) {
				return fmt.Errorf("rule %d uses unknown placeholder {%s}", ruleIndex, placeholder)
			}
		}
	}

	catchAllRule := rules[len(rules)-1]
	if !isCatchAllMatch(catchAllRule.Match) {
		return errors.New("the last rule must match every span")
	}
	for _, placeholder := range templatePlaceholders(catchAllRule.Template) {
		if !slices.Contains(alwaysAvailablePlaceholders, placeholder) {
			return fmt.Errorf("the last rule uses {%s}, which a span may not provide", placeholder)
		}
	}

	return nil
}

func templatePlaceholders(template string) []string {
	var placeholders []string
	for _, submatch := range narrativePlaceholderPattern.FindAllStringSubmatch(template, -1) {
		placeholders = append(placeholders, submatch[1])
	}

	return placeholders
}

func isKnownPlaceholder(placeholder string) bool {
	if attributeNames, isAttribute := strings.CutPrefix(placeholder, attributePlaceholderPrefix); isAttribute {
		return !slices.Contains(strings.Split(attributeNames, attributeAlternativesSeparator), "")
	}

	return slices.Contains(knownPlaceholders, placeholder)
}

func isCatchAllMatch(match narrativeMatch) bool {
	return len(match.Services) == 0 &&
		match.Kind == "" &&
		len(match.Names) == 0 &&
		match.NamePrefix == "" &&
		match.NameSuffix == "" &&
		len(match.Attributes) == 0
}

func (narrator *SpanNarrator) Describe(span projectedSpan) string {
	for _, rule := range narrator.rules {
		if !ruleMatchesSpan(rule.Match, span) {
			continue
		}
		if narrative, isComplete := renderNarrative(rule, span); isComplete {
			if span.Status == failedSpanStatus {
				return narrative + failedSpanNarrativeSuffix
			}
			return narrative
		}
	}

	return ""
}

func ruleMatchesSpan(match narrativeMatch, span projectedSpan) bool {
	if len(match.Services) > 0 && !slices.Contains(match.Services, span.ServiceName) {
		return false
	}
	if match.Kind != "" && match.Kind != span.Kind {
		return false
	}
	if len(match.Names) > 0 && !slices.Contains(match.Names, span.Name) {
		return false
	}
	if !strings.HasPrefix(span.Name, match.NamePrefix) || !strings.HasSuffix(span.Name, match.NameSuffix) {
		return false
	}
	for attributeName, expectedValue := range match.Attributes {
		if formatAttributeValue(span.Attributes[attributeName]) != expectedValue {
			return false
		}
	}

	return true
}

func renderNarrative(rule narrativeRule, span projectedSpan) (string, bool) {
	isComplete := true
	narrative := narrativePlaceholderPattern.ReplaceAllStringFunc(rule.Template, func(placeholderToken string) string {
		placeholderValue := resolvePlaceholder(placeholderToken[1:len(placeholderToken)-1], rule.Match, span)
		if placeholderValue == "" {
			isComplete = false
		}
		return placeholderValue
	})

	return narrative, isComplete
}

func resolvePlaceholder(placeholder string, match narrativeMatch, span projectedSpan) string {
	if attributeNames, isAttribute := strings.CutPrefix(placeholder, attributePlaceholderPrefix); isAttribute {
		for _, attributeName := range strings.Split(attributeNames, attributeAlternativesSeparator) {
			if attributeValue := formatAttributeValue(span.Attributes[attributeName]); attributeValue != "" {
				return attributeValue
			}
		}
		return ""
	}

	switch placeholder {
	case "service":
		return span.ServiceName
	case "name":
		return span.Name
	case "kind":
		return span.Kind
	case "duration":
		return formatSpanDuration(span.DurationMilliseconds)
	case "nameRemainder":
		return strings.TrimSuffix(strings.TrimPrefix(span.Name, match.NamePrefix), match.NameSuffix)
	default:
		return ""
	}
}

func formatAttributeValue(attributeValue any) string {
	if attributeValue == nil {
		return ""
	}

	return fmt.Sprint(attributeValue)
}

func formatSpanDuration(durationMilliseconds float64) string {
	switch {
	case durationMilliseconds >= millisecondsPerSecond:
		return fmt.Sprintf("%.2f s", durationMilliseconds/millisecondsPerSecond)
	case durationMilliseconds >= 1:
		return fmt.Sprintf("%.1f ms", durationMilliseconds)
	default:
		return fmt.Sprintf("%.2f ms", durationMilliseconds)
	}
}
