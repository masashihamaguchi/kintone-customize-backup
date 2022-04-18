from dotenv import load_dotenv
import datetime
import requests
import base64
import json
import git
import sys
import os
import shutil

# config
load_dotenv(override=True)
CONFIG = {
    'domain': os.getenv('KINTONE_DOMAIN'),
    'username': os.getenv('KINTONE_USERNAME'),
    'password': os.getenv('KINTONE_PASSWORD'),
    'repository': os.getenv('REPOSITORY_URL'),
    'directory': os.getenv('BACKUP_DIR') if os.getenv('BACKUP_DIR') is not None else 'backup'
}
AUTHORIZATION = base64.b64encode(f"{CONFIG['username']}:{CONFIG['password']}".encode())
APPS_DIR = CONFIG['directory'] + '/apps'


# for kintone
def get_app_list(a_list=None):
    app_list = [] if a_list is None else a_list
    url = f"https://{CONFIG['domain']}/k/v1/apps.json?offset={len(app_list)}&limit=100"
    res = requests.get(
        url,
        headers={
            'X-Cybozu-authorization': AUTHORIZATION
        }
    )

    if res.status_code != 200:
        return requests.exceptions.RequestException(f"エラーが発生しました。 status code: {res.status_code}")

    apps = res.json()['apps']
    app_list.extend(apps)

    if len(apps) >= 100:
        return get_app_list(app_list)
    else:
        return app_list


def get_customize_file_list(app_id):
    url = f"https://{CONFIG['domain']}/k/v1/app/customize.json?app={app_id}"
    return requests.get(
        url,
        headers={
            'X-Cybozu-authorization': AUTHORIZATION
        }
    ).json()


def get_customize_file(file_key):
    url = f"https://{CONFIG['domain']}/k/v1/file.json?fileKey={file_key}"
    return requests.get(
        url,
        headers={
            'X-Cybozu-authorization': AUTHORIZATION
        }
    ).content


# methods
def format_manifest_data(path, array):
    data = []
    for a in array:
        if a['type'] == 'URL':
            data.append(a)
        else:
            data.append({
                'type': a['type'],
                'path': path + '/' + a['file']['name']
            })

    return data


def get_date():
    t_delta = datetime.timedelta(hours=9)
    jst = datetime.timezone(t_delta, 'JST')
    now = datetime.datetime.now(jst)
    return '%s %s' % (now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'))


def init():
    # check dir
    os.makedirs(APPS_DIR, exist_ok=True)

    # git init and create remote
    repo = git.Repo.init(CONFIG['directory'])
    if 'origin' not in map(lambda r: r.name, repo.remotes):
        remote = repo.create_remote(name='origin', url=CONFIG['repository'])
        print(remote)

    print('initialization ok!')


def backup_files(app_list):
    for index, app in enumerate(app_list):

        print(f"\rcheck customize files {index + 1}/{len(app_list)}...", end='')
        app_id = app['appId']

        # get customize file list
        customize = get_customize_file_list(app_id)

        if 'code' in customize:
            app['number_of_files'] = 0
            continue

        # check files
        number_of_files = 0
        number_of_files += len(customize['desktop']['js'])
        number_of_files += len(customize['desktop']['css'])
        number_of_files += len(customize['mobile']['js'])
        number_of_files += len(customize['mobile']['css'])
        app['number_of_files'] = number_of_files

        if number_of_files == 0:
            continue

        # make dir
        os.makedirs(f"{APPS_DIR}/{app_id}", exist_ok=True)

        os.makedirs(f"{APPS_DIR}/{app_id}/desktop/js", exist_ok=True)
        os.makedirs(f"{APPS_DIR}/{app_id}/desktop/css", exist_ok=True)
        os.makedirs(f"{APPS_DIR}/{app_id}/mobile/js", exist_ok=True)
        os.makedirs(f"{APPS_DIR}/{app_id}/mobile/css", exist_ok=True)

        # save files
        for f in customize['desktop']['js']:
            if f['type'] == 'FILE':
                data = get_customize_file(f['file']['fileKey'])
                with open(f"{APPS_DIR}/{app_id}/desktop/js/{f['file']['name']}", "wb") as file:
                    file.write(data)

        for f in customize['desktop']['css']:
            if f['type'] == 'FILE':
                data = get_customize_file(f['file']['fileKey'])
                with open(f"{APPS_DIR}/{app_id}/desktop/css/{f['file']['name']}", "wb") as file:
                    file.write(data)

        for f in customize['mobile']['js']:
            if f['type'] == 'FILE':
                data = get_customize_file(f['file']['fileKey'])
                with open(f"{APPS_DIR}/{app_id}/mobile/js/{f['file']['name']}", "wb") as file:
                    file.write(data)

        for f in customize['mobile']['css']:
            if f['type'] == 'FILE':
                data = get_customize_file(f['file']['fileKey'])
                with open(f"{APPS_DIR}/{app_id}/mobile/css/{f['file']['name']}", "wb") as file:
                    file.write(data)

        # create manifest
        manifest = {
            'appId': app_id,
            'scope': customize['scope'],
            'files': {
                'desktop': {
                    'js': format_manifest_data('desktop/js', customize['desktop']['js']),
                    'css': format_manifest_data('desktop/css', customize['desktop']['css'])
                },
                'mobile': {
                    'js': format_manifest_data('desktop/js', customize['mobile']['js']),
                    'css': format_manifest_data('desktop/js', customize['mobile']['css'])
                }
            },
            'revision': customize['revision']
        }

        with open(f"{APPS_DIR}/{app_id}/manifest.json", 'w') as file:
            json.dump(manifest, file, ensure_ascii=False, indent=4)

    print("\033[2K\033[G" + "save completed!")


def generate_readme_and_ignore_file(app_list):
    date = get_date()
    number = 0
    rows = ''

    for app in app_list:
        if app['number_of_files'] > 0:
            number += 1

            row = f"| {app['appId']} | {app['name']} | [manifest.json](apps/{app['appId']}/manifest.json) |\n"
            rows += row

    readme = open('template/README.md', 'r', encoding="utf-8")
    text = readme.read()
    readme.close()

    text = text.replace('{domain}', f"https://{CONFIG['domain']}")
    text = text.replace('{date}', date)
    text = text.replace('{rows}', rows)
    text = text.replace('{number}', str(number))

    # create README.md
    with open('%s/README.md' % (CONFIG['directory']), 'w') as file:
        file.write(text)

    # create .gitignore
    shutil.copy('template/.gitignore', f"{CONFIG['directory']}/.gitignore")

    print(f"customize apps: {number}")


def git_commit_and_push():
    message = 'backup: %s' % (get_date())

    # git commit
    repo = git.Repo(CONFIG['directory'])
    repo.git.add('.')
    commit = repo.git.commit('.', message=message)
    print(commit)
    push = repo.git.push('origin', 'master')
    print(push)

    print('commit and push ok!')


# main
def main():
    # initialization
    init()

    # get apps list
    app_list = get_app_list()
    if type(app_list) is not list:
        print(app_list)
        return
    print(f"number of apps: {len(app_list)}")

    # backup customize files
    backup_files(app_list)

    # generate README.md
    generate_readme_and_ignore_file(app_list)

    # commit and push
    mode = sys.argv[0]
    if mode != 'local':
        git_commit_and_push()


if __name__ == '__main__':
    main()
