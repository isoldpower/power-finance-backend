package config

import (
	"errors"
	"path/filepath"
	"strings"

	"github.com/spf13/viper"
)

func ResolveViper(viperInstance *viper.Viper, configPath string) {
	configDir, configName, configType := SplitViperPath(configPath)

	viperInstance.AddConfigPath(configDir)
	viperInstance.SetConfigName(configName)
	viperInstance.SetConfigType(configType)
}

func TryResolveConfig(viperInstance *viper.Viper) error {
	viperInstance.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	viperInstance.AutomaticEnv()

	readErr := viperInstance.ReadInConfig()

	var missingConfigFile viper.ConfigFileNotFoundError
	if errors.As(readErr, &missingConfigFile) {
		return nil
	}

	return readErr
}

func SplitViperPath(path string) (configDir string, configName string, configType string) {
	configDir = filepath.Dir(path)
	configFullName := filepath.Base(path)
	configType = strings.TrimPrefix(filepath.Ext(configFullName), ".")
	configName = strings.TrimSuffix(configFullName, "."+configType)

	return configDir, configName, configType
}
