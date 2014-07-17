package log

import (
	"fmt"
	"os"
	"runtime"
	"time"
)

const (
	PREFIX      = "[TR]"
	TIME_FORMAT = "06-01-02 15:04:05"
)

var (
	NonColor    bool
	LEVEL_FLAGS = [...]string{"DEBUG", " INFO", " WARN", "ERROR", "FATAL"}
)

func init() {
	if runtime.GOOS == "windows" {
		NonColor = true
	}
}

const (
	DEBUG = iota
	INFO
	WARNING
	ERROR
	FATAL
)

func Print(level int, format string, args ...interface{}) {
	if NonColor {
		fmt.Printf("%s %s [%s] %s\n",
			PREFIX, time.Now().Format(TIME_FORMAT), LEVEL_FLAGS[level],
			fmt.Sprintf(format, args...))
		return
	}

	switch level {
	case DEBUG:
		fmt.Printf("%s \033[36m%s\033[0m [\033[34m%s\033[0m] %s\n",
			PREFIX, time.Now().Format(TIME_FORMAT), LEVEL_FLAGS[level],
			fmt.Sprintf(format, args...))
	case INFO:
		fmt.Printf("%s \033[36m%s\033[0m [\033[32m%s\033[0m] %s\n",
			PREFIX, time.Now().Format(TIME_FORMAT), LEVEL_FLAGS[level],
			fmt.Sprintf(format, args...))
	case WARNING:
		fmt.Printf("%s \033[36m%s\033[0m [\033[33m%s\033[0m] %s\n",
			PREFIX, time.Now().Format(TIME_FORMAT), LEVEL_FLAGS[level],
			fmt.Sprintf(format, args...))
	case ERROR:
		fmt.Printf("%s \033[36m%s\033[0m [\033[31m%s\033[0m] %s\n",
			PREFIX, time.Now().Format(TIME_FORMAT), LEVEL_FLAGS[level],
			fmt.Sprintf(format, args...))
	case FATAL:
		fmt.Printf("%s \033[36m%s\033[0m [\033[35m%s\033[0m] %s\n",
			PREFIX, time.Now().Format(TIME_FORMAT), LEVEL_FLAGS[level],
			fmt.Sprintf(format, args...))
		os.Exit(1)
	default:
		fmt.Printf("%s %s [%s] %s\n",
			PREFIX, time.Now().Format(TIME_FORMAT), LEVEL_FLAGS[level],
			fmt.Sprintf(format, args...))
	}
}

func Debug(format string, args ...interface{}) {
	Print(DEBUG, format, args...)
}

func Warn(format string, args ...interface{}) {
	Print(WARNING, format, args...)
}

func Info(format string, args ...interface{}) {
	Print(INFO, format, args...)
}

func Error(format string, args ...interface{}) {
	Print(ERROR, format, args...)
}

func Fatal(format string, args ...interface{}) {
	Print(FATAL, format, args...)
}
