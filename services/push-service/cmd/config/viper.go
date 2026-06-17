package config

import (
	"errors"
	"path/filepath"
	"strings"

	"github.com/spf13/viper"
)

// ResolveViper is used to configure Viper paths to be further utilised.
func ResolveViper(viperInstance *viper.Viper, configPath string) {
	configDir, configName, configType := SplitViperPath(configPath)

	viperInstance.AddConfigPath(configDir)
	viperInstance.SetConfigName(configName)
	viperInstance.SetConfigType(configType)
}

// TryResolveConfig is used after ResolveViper to try reading
// Viper config at configured paths.
func TryResolveConfig(viperInstance *viper.Viper) error {
	viperInstance.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	viperInstance.AutomaticEnv()

	readErr := viperInstance.ReadInConfig()
	if _, isOk := errors.AsType[viper.ConfigFileNotFoundError](readErr); isOk {
		return nil
	}

	return readErr
}

// SplitViperPath breaks down the path to directory, file name and file type.
func SplitViperPath(path string) (configDir string, configName string, configType string) {
	configDir = filepath.Dir(path)
	configFullName := filepath.Base(path)
	configType = strings.TrimPrefix(filepath.Ext(configFullName), ".")
	configName = strings.TrimSuffix(configFullName, "."+configType)

	return configDir, configName, configType
}
