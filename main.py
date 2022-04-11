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
def getAppList(app_list=[]):
    url = f"https://{CONFIG['domain']}/k/v1/apps.json?offset={len(app_list)}&limit=100"
    res = requests.get(
        url,
        headers = {
            'X-Cybozu-authorization': AUTHORIZATION
        }
    )

    if res.status_code != 200:
        return requests.exceptions.RequestException(f"エラーが発生しました。 status code: {res.status_code}")

    apps = res.json()['apps']
    app_list.extend(apps)

    if len(apps) >= 100:
        return getAppList(app_list)
    else:
        return app_list

def getCustomizeFileList(app_id):
    url = f"https://{CONFIG['domain']}/k/v1/app/customize.json?app={app_id}"
    return requests.get(
        url,
        headers = {
            'X-Cybozu-authorization': AUTHORIZATION
        }
    ).json()

def getCustomizeFile(fileKey):
    url = f"https://{CONFIG['domain']}/k/v1/file.json?fileKey={fileKey}"
    return requests.get(
        url,
        headers = {
            'X-Cybozu-authorization': AUTHORIZATION
        }
    ).content


# methods
def formatManifestData(path, array):
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

def getDate():
    t_delta = datetime.timedelta(hours=9)
    JST = datetime.timezone(t_delta, 'JST')
    now = datetime.datetime.now(JST)
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

def backupFiles(app_list):
    for index, app in enumerate(app_list):

        print(f"\rcheck customize files {index + 1}/{len(app_list)}...", end='')
        id = app['appId']
        
        # get customize file list
        customize = getCustomizeFileList(id)

        # check files
        number_of_files = 0
        number_of_files += len(customize['desktop']['js'])
        number_of_files += len(customize['desktop']['css'])
        number_of_files += len(customize['mobile']['js'])
        number_of_files += len(customize['mobile']['css'])
        app['number_of_files'] = number_of_files

        if number_of_files == 0: continue

        # make dir
        os.makedirs(f"{APPS_DIR}/{id}", exist_ok=True)

        os.makedirs(f"{APPS_DIR}/{id}/desktop/js", exist_ok=True)
        os.makedirs(f"{APPS_DIR}/{id}/desktop/css", exist_ok=True)
        os.makedirs(f"{APPS_DIR}/{id}/mobile/js", exist_ok=True)
        os.makedirs(f"{APPS_DIR}/{id}/mobile/css", exist_ok=True)

        # save files
        for f in customize['desktop']['js']:
            if f['type'] == 'FILE':
                data = getCustomizeFile(f['file']['fileKey'])
                with open(f"{APPS_DIR}/{id}/desktop/js/{f['file']['name']}", "wb") as file:
                    file.write(data)
        
        for f in customize['desktop']['css']:
            if f['type'] == 'FILE':
                data = getCustomizeFile(f['file']['fileKey'])
                with open(f"{APPS_DIR}/{id}/desktop/css/{f['file']['name']}", "wb") as file:
                    file.write(data)

        for f in customize['mobile']['js']:
            if f['type'] == 'FILE':
                data = getCustomizeFile(f['file']['fileKey'])
                with open(f"{APPS_DIR}/{id}/mobile/js/{f['file']['name']}", "wb") as file:
                    file.write(data)

        for f in customize['mobile']['css']:
            if f['type'] == 'FILE':
                data = getCustomizeFile(f['file']['fileKey'])
                with open(f"{APPS_DIR}/{id}/mobile/css/{f['file']['name']}", "wb") as file:
                    file.write(data)
        
        # create manifest
        manifest = {
            'appId': id,
            'scope': customize['scope'],
            'files': {
                'desktop': {
                    'js': formatManifestData('desktop/js', customize['desktop']['js']),
                    'css': formatManifestData('desktop/css', customize['desktop']['css'])
                },
                'mobile': {
                    'js':  formatManifestData('desktop/js', customize['mobile']['js']),
                    'css':  formatManifestData('desktop/js', customize['mobile']['css'])
                }
            },
            'revision': customize['revision']
        }

        with open(f"{APPS_DIR}/{id}/manifest.json", 'w') as file:
            json.dump(manifest, file, ensure_ascii=False, indent=4)

    print("\033[2K\033[G" + "save completed!")

def generateReadmeAndIgnoreFile(app_list):
    date = getDate()
    number = 0
    rows = ''

    for app in app_list:
        if app['number_of_files'] > 0:
            number += 1

            row = '| %s | %s | [manifest.json](%s) |\n' % (app['appId'], app['name'], 'apps/' + app['appId'] + '/manifest.json')
            rows += row

    readme = open('template/README.md')
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

def gitCommitAndPush():
    message = 'backup: %s' % (getDate())

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
    app_list = getAppList()
    if type(app_list) is not list:
        print(app_list)
        return
    print(f"number of apps: {len(app_list)}")

    # backup customize files
    backupFiles(app_list)

    # generate README.md
    generateReadmeAndIgnoreFile(app_list)

    # commit and push
    mode = sys.argv[0]
    if mode != 'local':
        gitCommitAndPush()


if __name__ == '__main__':
    main()
