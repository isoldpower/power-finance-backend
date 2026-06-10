package log

import (
	"fmt"
)

func Errorf(format string, args ...any) {
	prefix := getPrefix(LogTypeError)

	line := fmt.Sprintf(format, args...)
	fmt.Printf("%s%s", prefix, line)
}

func Errorln(format string, args ...any) {
	Errorf(format+"\n", args...)
}

func Infof(format string, args ...any) {
	if !isSilent {
		prefix := getPrefix(LogTypeInfo)
		line := fmt.Sprintf(format, args...)
		fmt.Printf("%s%s", prefix, line)
	}
}

func Infoln(format string, args ...any) {
	Infof(format+"\n", args...)
}

func Successf(format string, args ...any) {
	if !isSilent {
		prefix := getPrefix(LogTypeSuccess)
		line := fmt.Sprintf(format, args...)
		fmt.Printf("%s%s", prefix, line)
	}
}

func Successln(format string, args ...any) {
	Successf(format+"\n", args...)
}

func Logf(format string, args ...any) {
	if !isSilent {
		prefix := getPrefix(LogTypeDefault)
		line := fmt.Sprintf(format, args...)
		fmt.Printf("%s%s", prefix, line)
	}
}

func Logln(format string, args ...any) {
	Logf(format+"\n", args...)
}

func Debugf(format string, args ...any) {
	if isDebug && !isSilent {
		prefix := getPrefix(LogTypeDebug)
		line := fmt.Sprintf(format, args...)
		fmt.Printf("%s%s", prefix, line)
	}
}

func Debugln(format string, args ...any) {
	Debugf(format+"\n", args...)
}

func Processf(format string, args ...any) {
	if !isSilent {
		prefix := getPrefix(LogTypeProcess)
		line := fmt.Sprintf(format, args...)
		fmt.Printf("%s%s", prefix, line)
	}
}

func Processln(format string, args ...any) {
	Processf(format+"\n", args...)
}

func Warnf(format string, args ...any) {
	if !isSilent {
		prefix := getPrefix(LogTypeWarn)
		line := fmt.Sprintf(format, args...)
		fmt.Printf("%s%s", prefix, line)
	}
}

func Warnln(format string, args ...any) {
	Warnf(format+"\n", args...)
}
