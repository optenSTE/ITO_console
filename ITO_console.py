#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Консоль для выполнения внутренних комманд ИТО (измеритель тяжения оптический)

Используется API hyperion https://github.com/optenSTE/HyperionAPI

Usage: ITO_console.exe [ip] [command] [command] [command]...
        ip - IPv4 address of ITO, like 10.0.0.55
        command - one or more command to be send to ITO separated by a space,
                  like '#GetBoardTemperature #GetFirmwareVersion'
"""

import sys
import hyperion
import logging
from datetime import datetime

program_version = '20.10.2021'
extended_commands = {'sync_clock': 'set ITO clock by this PC time',
                     'sync_clock_utc': 'set ITO clock by this PC UTC-time (no time zone)'
                     }


def validate_ip(s):
    a = s.split('.')
    if len(a) != 4:
        return False
    for x in a:
        if not x.isdigit():
            return False
        i = int(x)
        if i < 0 or i > 255:
            return False
    return True


if __name__ == "__main__":
    commands_list = list()

    log_file_name = datetime.now().strftime(f'ITO_console_%Y%m%d%H%M%S.log')
    logging.basicConfig(format=u'[%(asctime)s]\t%(message)s',
                        level=logging.DEBUG, filename=log_file_name)

    logging.info(f'Program starts v.{program_version}')
    logging.info(f'{sys.argv}')

    print(""""Usage: ITO_console.exe [ip] [command] [command] [command]...
        ip - IPv4 address of ITO, like 10.0.0.55
        command - one or more command to be send to ITO separated by a space,
                  like '#GetBoardTemperature #GetFirmwareVersion'\n""")

    # разбор командной строки
    if len(sys.argv) <= 1:
        # exe only -> ask for ip
        ipAddress = input('Enter ITO IPv4 (eg. 10.0.0.55)>>')
    else:
        # exe + ip
        ipAddress = sys.argv[1]
        commands_list.extend([line.lower() for line in sys.argv[2:]])

    # check ip syntax
    if not validate_ip(ipAddress):
        msg = f"Wrong IP '{ipAddress}'"
        print(msg)
        logging.error(msg)
        sys.exit(0)

    # check connetction by Hyperion API command
    logging.info(f'Connect to {ipAddress}')
    try:
        response = hyperion.HCommTCPClient.hyperion_command(ipAddress, '#GetSerialNumber')
        print(response.message)
        logging.info(response.message)
    except Exception as e:
        print(f"Can't connect to IP '{ipAddress}': {str(e)}")
        logging.error(f"Can't connect to IP '{ipAddress}': {str(e)}")
        sys.exit(0)

    # get valid commands list
    hyperion_commands_list = list()
    try:
        response = hyperion.HCommTCPClient.hyperion_command(ipAddress, '#GetCommandNames')
    except Exception as e:
        msg = f"Can't connect to IP '{ipAddress}': {str(e)}"
        print(msg)
        logging.error(msg)
        sys.exit(0)
    else:
        hyperion_commands_list.extend([command.lower() for command in response.message.split('\r\n')])
        hyperion_commands_list.extend(extended_commands.keys())

    print("""Hyperion Commands begin with #.  
            Use #help for complete list of valid commands.
            Type "exit" to close the console.""")

    promptString = "hyp:" + response.content.decode() + ">>"

    while True:
        command = ''

        # ask for a command if commands list is empty
        if not commands_list:
            command = input(promptString).lower()

            if len(command) == 0:
                continue
            elif command.lower().find('exit') == 0:
                break
            elif command.partition(" ")[0] in hyperion_commands_list:
                # add one command
                commands_list.append(command)

        if commands_list:
            # обработаем список поступивших команд по одной, удаляя из списка
            command = commands_list[0]
            commands_list.pop(0)

        # команда должна быть в списке разрешенных команд
        if command.partition(" ")[0] not in hyperion_commands_list:
            msg = f'Command "{command}" skipped, not in the list of #GetCommandNames'
            print(msg)
            logging.info(msg)
            continue

        # встроенные команды ИТО начинаются с решетки
        if command[0] == "#":
            msg = f'>> {command}'
            print(msg)
            logging.info(msg)

            pCommand = command.partition(" ")
            try:
                response = hyperion.HCommTCPClient.hyperion_command(ipAddress, pCommand[0], pCommand[2])
            except hyperion.HyperionError as e:
                msg = "Hyperion Error " + e.string
                print(msg)
                logging.info(msg)
            else:
                msg = f'<< {response.message}\n'
                print(msg)
                logging.info(msg)

        # дополнительные команды - от меня
        elif 'sync_clock' in command.partition(" ")[0]:
            # установка часов ИТО по часам этого компьютера
            logging.info(command)
            msg = extended_commands[command.split()[0]]
            print(msg)
            logging.info(msg)

            if command.partition(" ")[0] == 'sync_clock':
                datetime_to_be_set = datetime.now()
            elif command.partition(" ")[0] == 'sync_clock_utc':
                datetime_to_be_set = datetime.utcnow()

            commands_list.insert(0, f"#SetInstrumentUtcDateTime {datetime_to_be_set.strftime('%Y %m %d %H %M %S')}".lower())
            commands_list.insert(1, f"#GetInstrumentUtcDateTime".lower())
