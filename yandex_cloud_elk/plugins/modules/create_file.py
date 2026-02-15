#!/usr/bin/python

# Copyright: (c) 2024, Your Name <your.email@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: create_file

short_description: Создает текстовый файл на удаленном хосте

version_added: "1.0.0"

description: Этот модуль создает текстовый файл на удаленном хосте с указанным содержимым и путем.

options:
    path:
        description: Полный путь, где должен быть создан файл на удаленном хосте.
        required: true
        type: str
    content:
        description: Содержимое для записи в файл.
        required: true
        type: str
    owner:
        description: Имя пользователя, который должен владеть файлом.
        required: false
        type: str
    group:
        description: Имя группы, которая должна владеть файлом.
        required: false
        type: str
    mode:
        description: Права доступа к файлу в восьмеричном формате (например, '0644').
        required: false
        type: str
    force:
        description: Если 'no', модуль завершится ошибкой, если файл уже существует.
        required: false
        type: bool
        default: true
    backup:
        description: Создать резервную копию, если файл уже существует.
        required: false
        type: bool
        default: false

author:
    - Your Name (@khurmatov)
'''

EXAMPLES = r'''
# Создание простого файла
- name: Создать конфигурационный файл
  my_own_namespace.my_collection.create_file:
    path: /etc/myapp/config.txt
    content: |
      # Конфигурационный файл для myapp
      debug=true
      port=8080

# Создание файла с определенными правами
- name: Создать файл с пользователем и правами
  my_namespace.my_collection.create_file:
    path: /home/user/script.sh
    content: "#!/bin/bash\necho 'Hello World'"
    owner: user
    group: users
    mode: '0755'

# Создание файла с резервной копией
- name: Создать файл с резервной копией
  my_namespace.my_collection.create_file:
    path: /var/log/app.log
    content: "Запись в лог"
    backup: true
'''

RETURN = r'''
path:
    description: Путь созданного/измененного файла.
    type: str
    returned: всегда
    sample: '/etc/myapp/config.txt'
content:
    description: Содержимое, которое было записано в файл.
    type: str
    returned: всегда
    sample: 'debug=true'
changed:
    description: Был ли файл создан или изменен.
    type: bool
    returned: всегда
    sample: true
backup_file:
    description: Путь к созданной резервной копии (если backup включен и файл существовал).
    type: str
    returned: когда backup включен и файл существовал
    sample: '/etc/myapp/config.txt.12345.2024-01-01@12:00:00~'
diff:
    description: Различия между старым и новым содержимым файла.
    type: dict
    returned: когда diff включен
    sample: '{"before": "старое содержимое", "after": "новое содержимое"}'
'''

import os
import tempfile
import shutil
from ansible.module_utils.basic import AnsibleModule


def write_file(module, path, content):
    """Запись содержимого в файл с правильной обработкой ошибок"""
    try:
        # Создать директорию, если она не существует
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, mode=0o755, exist_ok=True)

        # Записать содержимое в файл
        with open(path, 'w') as f:
            f.write(content)
        return True, None
    except (IOError, OSError) as e:
        return False, str(e)


def get_file_diff(module, path, content):
    """Создание diff между существующим файлом и новым содержимым"""
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                old_content = f.read()
            return {
                'before': old_content,
                'after': content
            }
    except (IOError, OSError):
        pass
    return None


def create_backup(module, path):
    """Создание резервной копии существующего файла"""
    try:
        if os.path.exists(path):
            backup_file = module.backup_local(path)
            return backup_file
    except Exception as e:
        module.warn(f"Не удалось создать резервную копию: {str(e)}")
    return None


def run_module():
    # Определение доступных аргументов/параметров, которые пользователь может передать модулю
    module_args = dict(
        path=dict(type='str', required=True),
        content=dict(type='str', required=True),
        owner=dict(type='str', required=False),
        group=dict(type='str', required=False),
        mode=dict(type='str', required=False),
        force=dict(type='bool', required=False, default=True),
        backup=dict(type='bool', required=False, default=False)
    )

    # Инициализация словаря результата
    result = dict(
        changed=False,
        path='',
        content=''
    )

    # Объект AnsibleModule будет нашей абстракцией для работы с Ansible
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        add_file_common_args=True
    )

    # Получение параметров
    path = module.params['path']
    content = module.params['content']
    force = module.params['force']
    backup = module.params['backup']

    # Проверка существования файла
    file_exists = os.path.exists(path)

    # Если force=False и файл существует, завершить с ошибкой
    if not force and file_exists:
        module.fail_json(msg=f"Файл '{path}' уже существует и force=no", **result)

    # Чтение существующего содержимого, если файл существует
    existing_content = None
    if file_exists:
        try:
            with open(path, 'r') as f:
                existing_content = f.read()
        except (IOError, OSError) as e:
            module.fail_json(msg=f"Не удалось прочитать существующий файл '{path}': {str(e)}", **result)

    # Определение необходимости изменения файла
    if not file_exists or existing_content != content:
        result['changed'] = True

    # Сохранение пути и содержимого в результате
    result['path'] = path
    result['content'] = content

    # Добавление информации о различиях, если включен check mode или diff
    if module._diff or module.check_mode:
        result['diff'] = get_file_diff(module, path, content)

    # Если в режиме проверки, вернуть результат досрочно
    if module.check_mode:
        module.exit_json(**result)

    # Если файл не нужно изменять, успешно завершить
    if not result['changed']:
        # Проверить атрибуты файла
        file_args = module.load_file_common_arguments(module.params)
        if module.set_fs_attributes_if_different(file_args, result['changed']):
            result['changed'] = True
        module.exit_json(**result)

    # Создание резервной копии, если запрошено и файл существует
    if backup and file_exists:
        backup_file = create_backup(module, path)
        if backup_file:
            result['backup_file'] = backup_file

    # Запись файла
    success, error_msg = write_file(module, path, content)
    if not success:
        module.fail_json(msg=f"Не удалось записать файл '{path}': {error_msg}", **result)

    # Установка атрибутов файла (владелец, группа, права)
    file_args = module.load_file_common_arguments(module.params)
    if module.set_fs_attributes_if_different(file_args, result['changed']):
        result['changed'] = True

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()