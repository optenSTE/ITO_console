# ITO_console
Консоль для выполнения внутренних комманд ИТО (измеритель тяжения оптический)

Используется API hyperion https://github.com/optenSTE/HyperionAPI

Usage:
```
ITO_console.exe [ip] [command] [command] [command]...
ip - IPv4 address of ITO, like 10.0.0.55
command - one or more command to be send to ITO separated by a space, like '#GetBoardTemperature #GetFirmwareVersion'
```

Дополнительные команды:
```
_sync_clock - установка часов ИТО по часам компьютера (используется часовой пояс)
_sуnc_clock_utс - установка часов ИТО по часам компьютера (время UTC)
_save_spectrum [spectrum_file_name] - запись спектра в текстовый файл
_get_config - сохранение конфигурации текущего прибора в виде скрипта с командами для последующего восстановления
_exit - выход из программы
```
