# kintone customize backup

## Overview

kintoneアプリのカスタマイズファイル（JavaScript / CSS）を一括でダウンロードし、リモートリポジトリにバックアップするためのプログラムです。

このプログラムを定期実行することで、カスタマイズファイルの定期バックアップを行うことができます。

kintone-customize-uploaderを使用したローカルでの開発を行わず、アプリの管理画面から「JSEdit for kintone」などのプラグインを使用してユーザーが直接カスタマイズファイルを編集する場合、バージョン管理やバックアップを行うことができないため、このようなシーンでの利用を想定しています。


## Usage

#### 1. 任意の場所にプロジェクトをクローンします

#### 2. Pythonパッケージをインストールします
```bash
$ pip install -r requirements.txt
```

#### 3. リモートリポジトリの設定

バックアップを行うリモートリポジトリを用意します。

リモートリポジトリとの接続はSSH等で設定をすることをおすすめします。

#### 4. 環境変数を設定します

`.env.example`をコピーして`.env`にファイル名を変更してください。
kintoneドメイン、ログイン名、パスワード、リモートリポジトリを設定してください。

|     variable     | required | description                                   |
|:----------------:|:--------:|:----------------------------------------------|
|  KINTONE_DOMAIN  |    ○     | kintoneドメイン<br>(your domain).cybozu.com       |
| KINTONE_USERNAME |    ○     | ログイン名                                         |
| KINTONE_PASSWORD |    ○     | パスワード                                         |
|  REPOSITORY_URL  |    ○     | リモートリポジトリのURL                                 |
|    BACKUP_DIR    |          | カスタマイズファイルを保存するディレクトリ<br>**※通常は変更しなくて大丈夫です。** |

カスタマイズファイルのバックアップを行うためには、ここで設定するユーザーにそのアプリのアプリ管理権限が付与されている必要があります。

全てのアプリのバックアップを行うには全てのアプリの管理権限を持っている必要があります。設定するユーザーの権限に注意してください。

`BACKUP_DIR`は通常は変更しないでください。変更する場合は`.gitignore`も変更してください。

#### 5. `main.py`を実行する

`main.py`を実行して正しくバックアップが行われることを確認してください。

```bash
$ python main.py
```

リモートリポジトリにpushを行わない場合は、コマンドの最後に`local`をつけます。

```bash
$ python main.py local
```

定期実行を行う場合は、各OSに合わせて設定を行ってください。

## Note

初期設定ではプロジェクトフォルダの中の`backup`ディレクトリにカスタマイズファイルが保存されてgitで管理されるようになっています。

特別な理由がない限りは変更しないことをおすすめします。

※プロジェクトフォルダと同じディレクトリを指定すると、リモートリポジトリへのPushができなくなってしまうので注意してください。

## Author

Masashi Hamaguchi<br>
masashi.hamaguchi@keio.jp

## License

The source code is licensed MIT.<br>
https://opensource.org/licenses/mit-license.php
