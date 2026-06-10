package log

import (
	"sync"
)

var (
	isSilent bool       = false
	isDebug  bool       = false
	logLevel int        = 1
	noIcons  bool       = false
	mutex    sync.Mutex = sync.Mutex{}
)

func SwitchSilent(silent bool) {
	isSilent = silent
}

func SwitchDebug(debug bool) {
	isDebug = debug
}

func IncreaseBy(step int) {
	logLevel += step
}

func DecreaseBy(step int) {
	if logLevel > step {
		logLevel -= step
	}
}

func SwitchIcons(icons bool) {
	noIcons = !icons
}

func IncreaseLevel() {
	IncreaseBy(1)
}

func DecreaseLevel() {
	DecreaseBy(1)
}
