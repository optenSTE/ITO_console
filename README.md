# ITO_console
Консоль для выполнения внутренних комманд ИТО (измеритель тяжения оптический)

Используется API hyperion https://github.com/optenSTE/HyperionAPI

Usage: ITO_console.exe [ip] [command] [command] [command]...

        ip - IPv4 address of ITO, like 10.0.0.55
        command - one or more command to be send to ITO separated by a space,
                  like '#GetBoardTemperature #GetFirmwareVersion'
