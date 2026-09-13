package tracing

import (
	"os"
	"strconv"
	"strings"
)

const (
	EnvironmentVariableServiceName           = "OTEL_SERVICE_NAME"
	EnvironmentVariableExporterEndpoint      = "OTEL_EXPORTER_OTLP_ENDPOINT"
	EnvironmentVariableSDKDisabled           = "OTEL_SDK_DISABLED"
	EnvironmentVariableSamplerRatio          = "OTEL_TRACES_SAMPLER_ARG"
	EnvironmentVariableDeploymentEnvironment = "OTEL_DEPLOYMENT_ENVIRONMENT"

	defaultDeploymentEnvironment = "development"
	defaultSamplerRatio          = 1.0
)

type Settings struct {
	ServiceName           string
	ExporterEndpoint      string
	SamplerRatio          float64
	DeploymentEnvironment string
	IsEnabled             bool
}

func ResolveSettings(defaultServiceName string) Settings {
	exporterEndpoint := strings.TrimSpace(os.Getenv(EnvironmentVariableExporterEndpoint))

	serviceName := strings.TrimSpace(os.Getenv(EnvironmentVariableServiceName))
	if serviceName == "" {
		serviceName = defaultServiceName
	}

	deploymentEnvironment := strings.TrimSpace(os.Getenv(EnvironmentVariableDeploymentEnvironment))
	if deploymentEnvironment == "" {
		deploymentEnvironment = defaultDeploymentEnvironment
	}

	return Settings{
		ServiceName:           serviceName,
		ExporterEndpoint:      exporterEndpoint,
		SamplerRatio:          resolveSamplerRatio(),
		DeploymentEnvironment: deploymentEnvironment,
		IsEnabled:             exporterEndpoint != "" && !isTrueLike(os.Getenv(EnvironmentVariableSDKDisabled)),
	}
}

func resolveSamplerRatio() float64 {
	rawRatio := strings.TrimSpace(os.Getenv(EnvironmentVariableSamplerRatio))
	if rawRatio == "" {
		return defaultSamplerRatio
	}

	parsedRatio, parseErr := strconv.ParseFloat(rawRatio, 64)
	if parseErr != nil {
		return defaultSamplerRatio
	}

	return parsedRatio
}

func isTrueLike(rawValue string) bool {
	switch strings.ToLower(strings.TrimSpace(rawValue)) {
	case "1", "true", "yes", "on":
		return true
	default:
		return false
	}
}
