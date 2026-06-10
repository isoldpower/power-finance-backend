package log

type Icon string

const (
	GearIcon      Icon = "⚙️"
	BanIcon       Icon = "🚫 "
	CheckIcon     Icon = "✅  "
	RocketIcon    Icon = "🚀 "
	WarnIcon      Icon = "⚠️ "
	PencilIcon    Icon = "✏️ "
	TerminateIcon Icon = "💥"
	BoxIcon       Icon = "📦"
	KnifeIcon     Icon = "🔪"
	AttentionIcon Icon = "❗"
)

func GetIcon(icon Icon) string {
	if noIcons {
		return ""
	}

	return string(icon)
}
