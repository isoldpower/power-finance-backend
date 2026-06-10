package color

import "fmt"

type Color string

const (
	BlackColor   Color = "black"
	RedColor     Color = "red"
	GreenColor   Color = "green"
	YellowColor  Color = "yellow"
	BlueColor    Color = "blue"
	MagentaColor Color = "magenta"
	CyanColor    Color = "cyan"
	WhiteColor   Color = "white"

	BoldCode          = "\033[1m"
	UnderlineCode     = "\033[4m"
	ItalicCode        = "\033[3m"
	StrikethroughCode = "\033[9m"
	ResetCode         = "\033[0m"
)

type colorCodes struct {
	background string
	foreground string
}

var (
	colorful = true
	colorMap = map[Color]colorCodes{
		BlackColor: colorCodes{
			foreground: "\033[30m",
			background: "\033[40m",
		},
		RedColor: colorCodes{
			foreground: "\033[31m",
			background: "\033[41m",
		},
		GreenColor: colorCodes{
			foreground: "\033[32m",
			background: "\033[42m",
		},
		YellowColor: colorCodes{
			foreground: "\033[33m",
			background: "\033[43m",
		},
		BlueColor: colorCodes{
			foreground: "\033[34m",
			background: "\033[44m",
		},
		MagentaColor: colorCodes{
			foreground: "\033[35m",
			background: "\033[45m",
		},
		CyanColor: colorCodes{
			foreground: "\033[36m",
			background: "\033[46m",
		},
		WhiteColor: colorCodes{
			foreground: "\033[37m",
			background: "\033[47m",
		},
	}
)

func SetEnabled(enabled bool) {
	colorful = enabled
}

func Black(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[BlackColor].foreground, text, ResetCode)
}

func BgBlack(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[BlackColor].background, text, ResetCode)
}

func Red(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[RedColor].foreground, text, ResetCode)
}

func BgRed(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[RedColor].background, text, ResetCode)
}

func Green(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[GreenColor].foreground, text, ResetCode)
}

func BgGreen(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[GreenColor].background, text, ResetCode)
}

func Yellow(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[YellowColor].foreground, text, ResetCode)
}

func BgYellow(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[YellowColor].background, text, ResetCode)
}

func Blue(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[BlueColor].foreground, text, ResetCode)
}

func BgBlue(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[BlueColor].background, text, ResetCode)
}

func Magenta(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[MagentaColor].foreground, text, ResetCode)
}

func BgMagenta(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[MagentaColor].background, text, ResetCode)
}

func Cyan(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[CyanColor].foreground, text, ResetCode)
}

func BgCyan(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[CyanColor].background, text, ResetCode)
}

func White(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[WhiteColor].foreground, text, ResetCode)
}

func BgWhite(text string) string {
	if colorful == false {
		return text
	}

	return fmt.Sprintf("%s%s%s", colorMap[WhiteColor].background, text, ResetCode)
}

func Bold(text string) string {
	return fmt.Sprintf("%s%s%s", BoldCode, text, ResetCode)
}

func Underline(text string) string {
	return fmt.Sprintf("%s%s%s", UnderlineCode, text, ResetCode)
}

func Italic(text string) string {
	return fmt.Sprintf("%s%s%s", ItalicCode, text, ResetCode)
}

func Strikethrough(text string) string {
	return fmt.Sprintf("%s%s%s", StrikethroughCode, text, ResetCode)
}
