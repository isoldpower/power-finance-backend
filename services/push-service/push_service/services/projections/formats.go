package projections

func severityName(protoName string) string {
	if name, known := severityNames[protoName]; known {
		return name
	}

	return defaultSeverity
}

func subjectOf(payload notificationCreatedPayload) *subject {
	if payload.SubjectType == "" || payload.SubjectID == "" {
		return nil
	}

	return &subject{
		Type: payload.SubjectType,
		ID:   payload.SubjectID,
	}
}
