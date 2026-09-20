package tracing

import "testing"

func clearTracingEnvironment(t *testing.T) {
	t.Helper()

	for _, name := range []string{
		EnvironmentVariableServiceName,
		EnvironmentVariableExporterEndpoint,
		EnvironmentVariableSDKDisabled,
		EnvironmentVariableSamplerRatio,
		EnvironmentVariableDeploymentEnvironment,
	} {
		t.Setenv(name, "")
	}
}

func TestDefaultsApplyWithoutEnvironment(t *testing.T) {
	clearTracingEnvironment(t)

	settings := ResolveSettings("write-service")

	if settings.ServiceName != "write-service" {
		t.Fatalf("expected the default service name, got %q", settings.ServiceName)
	}
	if settings.DeploymentEnvironment != defaultDeploymentEnvironment {
		t.Fatalf("unexpected deployment environment %q", settings.DeploymentEnvironment)
	}
	if settings.SamplerRatio != defaultSamplerRatio {
		t.Fatalf("unexpected sampler ratio %v", settings.SamplerRatio)
	}
	if settings.IsEnabled {
		t.Fatal("expected tracing to be disabled without an exporter endpoint")
	}
}

func TestEnvironmentOverridesServiceNameAndEndpoint(t *testing.T) {
	clearTracingEnvironment(t)
	t.Setenv(EnvironmentVariableServiceName, "read-service")
	t.Setenv(EnvironmentVariableExporterEndpoint, "http://jaeger:4317")

	settings := ResolveSettings("write-service")

	if settings.ServiceName != "read-service" {
		t.Fatalf("unexpected service name %q", settings.ServiceName)
	}
	if !settings.IsEnabled {
		t.Fatal("expected an exporter endpoint to enable tracing")
	}
}

func TestSDKDisabledWinsOverAnEndpoint(t *testing.T) {
	clearTracingEnvironment(t)
	t.Setenv(EnvironmentVariableExporterEndpoint, "http://jaeger:4317")
	t.Setenv(EnvironmentVariableSDKDisabled, "true")

	if ResolveSettings("write-service").IsEnabled {
		t.Fatal("expected OTEL_SDK_DISABLED to disable tracing")
	}
}

func TestMalformedSamplerRatioFallsBackToTheDefault(t *testing.T) {
	clearTracingEnvironment(t)
	t.Setenv(EnvironmentVariableSamplerRatio, "not-a-number")

	if ratio := ResolveSettings("write-service").SamplerRatio; ratio != defaultSamplerRatio {
		t.Fatalf("expected the default ratio, got %v", ratio)
	}
}

func TestStripSchemeLeavesABareHostPort(t *testing.T) {
	for _, endpoint := range []string{"http://jaeger:4317", "https://jaeger:4317/", "jaeger:4317"} {
		if stripped := stripScheme(endpoint); stripped != "jaeger:4317" {
			t.Fatalf("expected jaeger:4317 from %q, got %q", endpoint, stripped)
		}
	}
}
