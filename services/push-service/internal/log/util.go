package log

import (
	"encoding/json"
	"fmt"
	"strings"
)

type LogType string

const (
	LogTypeDebug   LogType = LogType(GearIcon)
	LogTypeError   LogType = LogType(BanIcon)
	LogTypeSuccess LogType = LogType(CheckIcon)
	LogTypeProcess LogType = LogType(RocketIcon)
	LogTypeInfo    LogType = LogType(PencilIcon)
	LogTypeWarn    LogType = LogType(WarnIcon)
	LogTypeDefault LogType = ""
)

func getPrefix(logType LogType) string {
	icon := string(logType)
	if noIcons {
		icon = ""
	}

	return fmt.Sprintf("%s %s", strings.Repeat("    ", logLevel-1), icon)
}

func GetObjectPattern(value interface{}) string {
	indent := strings.Repeat("┆  ", logLevel)

	marshalled, _ := json.MarshalIndent(value, "", indent)
	return "\n" + string(marshalled)
}

func RaiseLog(log func()) {
	mutex.Lock()
	defer mutex.Unlock()

	IncreaseLevel()
	defer DecreaseLevel()

	log()
}

func PrintError(comments string, err error) {
	Errorln(comments, err)
	RaiseLog(func() {
		Logln("%s %s", GetIcon(TerminateIcon), err.Error())
	})
}
