#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Консоль для выполнения внутренних комманд ИТО (измеритель тяжения оптический)

Используется API hyperion https://github.com/optenSTE/HyperionAPI

Usage: ITO_console.exe [ip] [command1] [command2] [param1] [param2]... [command3]...
        ip - IPv4 address of ITO, like 10.0.0.55
        command - one or more command to be send to ITO separated by a space,
                  like '#GetBoardTemperature'
"""

# speed of light and fiber index of refraction for delays ns to m conversion
c = 299792458
n = 1.4682

import sys
import hyperion
import logging
from datetime import datetime

program_version = '03.11.2021'

# name_of_command: command_description
extended_commands_list = {'_sync_clock': 'set ITO clock by this PC time',
                          '_sync_clock_utc': 'set ITO clock by this PC UTC-time (no time zone)',
                          '_save_spectrum': 'save full spectrum to file',
                          '_load_commands': 'load commands sequence from file (each command in new line)',
                          '_get_config': 'read all important commands'
                          }


def validate_ip(s):
    a = s.split('.')
    if len(a) != 4:
        return False
    for x in a:
        if not x.isdigit():
            return False
        if not 0 <= int(x) <= 255:
            return False
    return True


def execute_command(command):
    try:
        resp = hyperion.HCommTCPClient.hyperion_command(ipAddress, command.partition(" ")[0], command.partition(" ")[2])
    except hyperion.HyperionError as e:
        msg = "Hyperion Error " + e.string
        print(msg)
        logging.info(msg)
    else:
        return resp


if __name__ == "__main__":
    commands_list = list()

    log_file_name = datetime.now().strftime(f'ITO_console_%Y%m%d%H%M%S.log')
    logging.basicConfig(format=u'[%(asctime)s]\t%(message)s',
                        level=logging.DEBUG, filename=log_file_name)

    logging.info(f'Program starts v.{program_version}')
    logging.info(f'{sys.argv}')

    print("""Usage: ITO_console.exe [ip] [command] [command] [command]...
        ip - IPv4 address of ITO, like 10.0.0.55
        command - one or more command to be send to ITO separated by a space,
                  like '#GetBoardTemperature #GetFirmwareVersion'""")
    print("""Hyperion Commands begin with #.  
        Use #help for complete list of valid commands.
        Type "exit" to close the console.""")
    print(f'Console built-in commands:')
    for key, value in extended_commands_list.items():
        print(f'\t{key} - {value}')
    print('\n')

    # если нет IP-адреса, то его нужно запросить
    if len(sys.argv) <= 1:
        # exe only -> ask for ip
        ipAddress = input('Enter ITO IPv4 (eg. 10.0.0.55)>>')
    else:
        ipAddress = sys.argv[1]

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
        hyperion_commands_list.extend(extended_commands_list.keys())

    # вытащить список команд из командной строки
    if len(sys.argv) > 2:
        # команды и их параметры разделены пробелами - нужно корректно отличить одно от другого
        for text in sys.argv[2:]:
            if text.lower() in hyperion_commands_list:
                # получили имя команды
                commands_list.append(text.lower())
            elif commands_list:
                # получили параметр для предыдущей команды (если она есть)
                commands_list[-1] = commands_list[-1] + ' ' + text

    promptString = "hyp:" + response.content.decode() + ">>"

    h1 = hyperion.Hyperion(ipAddress)

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

        pCommand = command.partition(" ")

        # встроенные команды ИТО начинаются с решетки
        if command[0] == "#":
            msg = f'>> {command}'
            print(msg)
            logging.info(msg)

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
        elif command[0] == "_":
            if '_sync_clock' in pCommand[0]:
                # установка часов ИТО по часам этого компьютера
                logging.info(command)
                msg = extended_commands_list[command.split()[0]]
                print(msg)
                logging.info(msg)

                if pCommand[0] == 'sync_clock':
                    datetime_to_be_set = datetime.now()
                elif pCommand[0] == 'sync_clock_utc':
                    datetime_to_be_set = datetime.utcnow()
                else:
                    continue

                # добавим команды на установку времени в конвейр команд - исполнятся в следующих циклах
                commands_list.insert(0, f"#SetInstrumentUtcDateTime {datetime_to_be_set.strftime('%Y %m %d %H %M %S')}".lower())
                commands_list.insert(1, f"#GetInstrumentUtcDateTime".lower())

            elif pCommand[0] == '_save_spectrum':
                # save full spectrum to file
                logging.info(command)
                msg = extended_commands_list[command.split()[0]]
                print(msg)
                logging.info(msg)

                # имя файла для записи спектра может быть задано, либо сгенерировано
                if pCommand[2]:
                    spectrum_file_name = pCommand[2]
                else:
                    spectrum_file_name = datetime.now().strftime(f'spectrum_%Y%m%d%H%M%S.txt')

                # получение спектров
                try:
                    logging.info('getting spectra...')
                    spectrum = h1.spectra

                    logging.info('saving spectra...')
                    k = zip(spectrum.wavelengths, *spectrum.data)
                    with open(spectrum_file_name, 'w') as spectrum_file:
                        for i in k:
                            print('\t'.join(str(x) for x in i), file=spectrum_file)
                except Exception as e:
                    logging.error(f'some error during getting spectra - exception: {e.__doc__}')
            elif '_load_commands' in pCommand[0]:
                # load commands sequence from file (each command in new line)
                # ';' sing means comment
                if not pCommand[2]:
                    logging.error('_load_commands should have file name')
                with open(pCommand[2]) as f:
                    for line in f.readlines():
                        if len(line.split(";")[0]) >= len('#help'):
                            commands_list.insert(1, line.split(";")[0].lower())
            elif '_get_config' in pCommand[0]:
                # read all important commands

                # имя выходного файла может быть задано, либо сгенерировано
                if pCommand[2]:
                    out_file_name = pCommand[2]
                else:
                    out_file_name = f'{ipAddress.replace(".", "_")}_apply_commands.txt'

                with open(out_file_name, 'w') as f:
                    logging.info(f'The number of channels on the instrument - {h1.channel_count}')
                    logging.info(f'The maximum number of peaks that can be returned on any channel - {h1.max_peak_count_per_channel}')
                    logging.info(f'The user programmable name of the instrument (settable) - {h1.instrument_name}')
                    logging.info(f'The version of FPGA code on the instrument - {h1.fpga_version}')
                    logging.info(f'The version of firmware on the instrument - {h1.firmware_version}')
                    logging.info(f'The instrument serial number - {h1.serial_number}')

                    f.write('\n; ***** SYSTEM *****\n')
                    f.write(f'#SetInstrumentName {h1.instrument_name}\n')
                    f.write('\n')

                    f.write('\n; ***** ACQUISITION *****\n')
                    f.write('; Active full spectrum channels settings - channels for which full spectrum data is acquired\n')
                    w = h1.active_full_spectrum_channel_numbers
                    if len(w) == 0:
                        w_str = 'no active channels'
                    else:
                        w_str = ', '.join([str(x) for x in w])

                        f.write('#SetActiveFullSpectrumDutChannelNumbers ' + ' '.join([str(x) for x in w]) + '\n')
                    f.write('\n')
                    logging.info(f'The channels for which full spectrum data is acquired - {w_str}')

                    f.write('\n; ***** LASER *****\n')
                    # laser_scan_speed
                    w_str = ', '.join([str(x) for x in h1.available_laser_scan_speeds])
                    logging.info(f'Available laser scan speeds that are settable on the instrument - {w_str}')
                    logging.info(f'The current laser scan speed of the instrument - {h1.laser_scan_speed}')

                    f.write('\n; ***** HOST *****\n')
                    logging.info(f'The UTC time on the instrument.  If set, this will be overwritten by NTP or PTP if enabled. - {h1.instrument_utc_date_time}')
                    logging.info(f'Boolean value indicating the enabled state of the Network Time Protocol for automatic time synchronization. - {h1.ntp_enabled}')
                    logging.info(f'String containing the IP address of the NTP server. - {h1.ntp_server}')
                    logging.info(f'Boolean value indicating the enabled state of the precision time protocol.  Note that this cannot be enabled at the same time as NTP. - {h1.ptp_enabled}')
                    if h1.ntp_enabled:
                        f.write('#SetNtpEnabled 1\n')
                        f.write(f'#SetNtpServer {h1.ntp_server}\n')
                    else:
                        f.write('#SetNtpEnabled 0\n')
                    if h1.ptp_enabled:
                        f.write('#SetPtpEnabled 1\n')
                    else:
                        f.write('#SetPtpEnabled 0\n')
                    f.write('\n')

                    f.write('\n; ***** DETECTION *****\n')
                    f.write('; Peak offsets (SoL compensation)\n')
                    logging.info(f'The peak offsets used for time of flight distance compensation: ch - offsets (dist[m], wl[nm])')
                    for ch in range(1, h1.channel_count+1):
                        peak_offsets = h1.get_peak_offsets(ch)

                        # в лог записываются читаемые величины - нанометры и метры
                        boundaries_nm = [round(h1.convert_counts_to_wavelengths(nm)[0], 3) for nm in peak_offsets.boundaries]
                        delays_m = [round(delay_ns*1e-9*c/2/n) for delay_ns in peak_offsets.delays]
                        o = list(zip(delays_m, boundaries_nm))
                        if len(o) == 0:
                            o = 'no offsets'
                        else:
                            o = f'{o}'[1:-1]
                        logging.info(f'{ch} - {o}')

                        o = list(zip(peak_offsets.delays, peak_offsets.boundaries))
                        if len(o) == 0:
                            f.write(f'#ClearPeakOffsets {ch}\n')
                        else:
                            o_counts = [ch, len(o)] + [i for sub in o for i in sub]
                            o_str = [str(i) for i in o_counts]
                            f.write('#SetPeakOffsets ' + ' '.join(o_str) + '\n')

                    f.write('\n; Peak detection settings\n')
                    # нужно сначала удалить все пользовательские пресеты из прибора, а чтобы это сделать - назначить на ве каналы настройки из заводских пресетов.
                    # только после этого можно вносить новые пользовательские пресеты и назначать их каналам

                    f.write('; 1. assigning factory presets to all channels (ID 128)\n')
                    for ch in range(1, h1.channel_count+1):
                        f.write(f'#SetChannelDetectionSettingId {ch} 128\n')
                    f.write('\n; 2. removing all user presets\n')
                    for user_preset_id in range(128):
                        f.write(f'#RemoveDetectionSetting {user_preset_id}\n')

                    used_pd_presets = list()  # список всех используемых пресетов текущего прибора
                    for ch in range(1, h1.channel_count+1):
                        cur_ch_pd_preset = h1.get_channel_detection_setting(ch)
                        if cur_ch_pd_preset not in used_pd_presets:
                            used_pd_presets.append(cur_ch_pd_preset)

                    f.write('\n; 3. adding new user presets\n')
                    for preset in used_pd_presets:
                        if preset.setting_id < 128:
                            # убрать переносы строк, чтобы не мешались
                            preset.name = preset.name.replace('\n', '')
                            preset.description = preset.description.replace('\n', '')

                            f.write(f"#AddDetectionSetting {preset.setting_id} '{preset.name}' '{preset.description}' {preset.boxcar_length} {preset.diff_filter_length} {preset.lockout} {preset.threshold} {0 if preset.mode=='Valley' else 1}\n")
                    f.write('\n; 4. assigning presets to channels\n')
                    for ch in range(1, h1.channel_count+1):
                        cur_ch_pd_preset = h1.get_channel_detection_setting(ch)
                        f.write(f"#SetChannelDetectionSettingId {ch} {cur_ch_pd_preset.setting_id}\n")

                    f.write('\n')

                    f.write('\n; ***** NETWORK *****\n')
                    # network settings. It must be the last one - the connection may be lost after changing the IP address.
                    network_mode = h1.network_ip_mode
                    if network_mode.lower() == 'static':
                        f.write('#EnableStaticIpMode\n')
                    else:
                        f.write('#EnableDynamicIpMode\n')
                    network_settings = h1.active_network_settings
                    f.write(f'#SetStaticNetworkSettings {network_settings.address} {network_settings.netmask} {network_settings.gateway}\n')
                    logging.info(f'The network address, netmask, and gateway that are currently active on the instrument - {h1.active_network_settings}')
                    logging.info(f'The network address, netmask, and gateway that are active when the instrument is in static mode - {h1.static_network_settings}')
                    logging.info(f'The network ip configuration mode, can be dhcp or dynamic for DHCP mode, or static for static mode - {h1.network_ip_mode}')
                    f.write('\n')
