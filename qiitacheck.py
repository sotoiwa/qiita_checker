#!/usr/bin/env python3

import argparse
import csv
import json
import logging
import os
import sys

import prettytable
import requests


formatter = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
logging.basicConfig(level=logging.WARNING, format=formatter)
logger = logging.getLogger(__name__)


def get_next_url(response):
    """次のページがある場合は'rel="next"'としてurlが含まれるので、urlを抽出して返す。
    ない場合はNoneを返す。

    link: <https://qiita.com/api/v2/authenticated_user/items?page=1>;
    rel="first", <https://qiita.com/api/v2/authenticated_user/items?page=2>;
    rel="next", <https://qiita.com/api/v2/authenticated_user/items?page=4>;
    rel="last"

    :param response:
    :return: 次のurl
    """
    link = response.headers['link']
    if link is None:
        return None

    links = link.split(',')

    for link in links:

        if 'rel="next"' in link:
            return link[link.find('<') + 1:link.find('>')]
    return None


def get_items(token):
    """ページネーションして全ての記事を取得し、
    ストック数とビュー数は一覧に含まれないので、それらの情報も追加して返す。

    :param token:
    :return: 記事のリスト
    """

    url = 'https://qiita.com/api/v2/authenticated_user/items'
    headers = {'Authorization': 'Bearer {}'.format(token)}

    items = []
    while True:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        items.extend(json.loads(response.text))
        logger.info('GET {}'.format(url))
        # 次のurlがあるかを確認する
        url = get_next_url(response)
        if url is None:
            break

    # 各記事についてビュー数とストック数の情報を取得して追加する
    # page_views_countは一覧APIにもフィールドはあるがnullが返ってくる
    for item in items:

        # ビュー数
        url = 'https://qiita.com/api/v2/items/{}'.format(item['id'])
        logger.info('GET {}'.format(url))
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        item['page_views_count'] = json.loads(response.text)['page_views_count']

        # ストック数
        url = 'https://qiita.com/api/v2/items/{}/stockers'.format(item['id'])
        logger.info('GET {}'.format(url))
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        stockers = json.loads(response.text)
        item['stocks_count'] = len(stockers)

    return items


def get_item_detail(token, item_id):
    """指定の記事を取得し、いいねしたユーザーとストックしたユーザーを追加して返す。

    :param token:
    :param item_id:
    :return: 記事
    """

    headers = {'Authorization': 'Bearer {}'.format(token)}

    url = 'https://qiita.com/api/v2/items/{}'.format(item_id)
    logger.info('GET {}'.format(url))
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    item = json.loads(response.text)

    # ストック数、ストックしたユーザー
    url = 'https://qiita.com/api/v2/items/{}/stockers'.format(item_id)
    logger.info('GET {}'.format(url))
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    stockers = json.loads(response.text)
    item['stocks_count'] = len(stockers)
    item['stockers'] = []
    for stocker in stockers:
        item['stockers'].append({
            'id': stocker['id'],
            'name': stocker['name']
        })

    # いいねしたユーザー
    url = 'https://qiita.com/api/v2/items/{}/likes'.format(item_id)
    logger.info('GET {}'.format(url))
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    likers = json.loads(response.text)
    item['likers'] = []
    for liker in likers:
        item['likers'].append({
            'id': liker['user']['id'],
            'name': liker['user']['name']
        })

    return item


def sort_items(items, sort_by, reverse):
    """リストをソートする

    :param items:
    :param sort_by:
    :param reverse:
    :return:
    """

    if sort_by == 'views':
        if reverse:
            items.sort(key=lambda x: -x['page_views_count'])
        else:
            items.sort(key=lambda x: x['page_views_count'])
    elif sort_by == 'likes':
        if reverse:
            items.sort(key=lambda x: -x['likes_count'])
        else:
            items.sort(key=lambda x: x['likes_count'])
    elif sort_by == 'stocks':
        if reverse:
            items.sort(key=lambda x: -x['stocks_count'])
        else:
            items.sort(key=lambda x: x['stocks_count'])


def output_text(items, filepath):
    """テキストで整形して標準出力に出力する。
    ファイル名が指定された場合はファイルに出力する。

    :param items:
    :param filepath:
    :return:
    """

    table = prettytable.PrettyTable()
    table.field_names = ['Title', 'Views', 'Likes', 'Stocks', 'Id']
    table.align['Title'] = 'l'
    table.align['Views'] = 'r'
    table.align['Likes'] = 'r'
    table.align['Stocks'] = 'r'
    table.align['Id'] = 'l'
    for item in items:
        table.add_row([item['title'],
                       item['page_views_count'],
                       item['likes_count'],
                       item['stocks_count'],
                       item['id']])

    if filepath:
        with open(filepath, 'w') as text_file:
            text_file.write(table.get_string())
    else:
        print(table)


def output_csv(items, filepath):
    """csvに整形して標準出力に出力する。
    ファイル名が指定された場合はファイルに出力する。

    :param items:
    :param filepath:
    :return:
    """

    def write_rows(writer, items):
        for item in items:
            writer.writerow({
                'Title': item['title'],
                'Views': item['page_views_count'],
                'Likes': item['likes_count'],
                'Stocks': item['stocks_count'],
                'Id': item['id']
            })

    fieldnames = ['Title', 'Views', 'Likes', 'Stocks', 'Id']
    if filepath:
        with open(filepath, 'w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            write_rows(writer, items)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        write_rows(writer, items)


def output_json(items, filepath):
    """jsonに整形して標準出力に出力する。
    ファイル名が指定された場合はファイルに出力する。

    :param items:
    :param filepath:
    :return:
    """

    my_list = []
    for item in items:
        my_list.append({
            'Title': item['title'],
            'Views': item['page_views_count'],
            'Likes': item['likes_count'],
            'Stocks': item['stocks_count'],
            'Id': item['id']
        })

    if filepath:
        with open(filepath, 'w') as json_file:
            json.dump(my_list, json_file, ensure_ascii=False, indent=4)
    else:
        print(json.dumps(my_list, ensure_ascii=False, indent=4))


def output_items(token, args):
    """記事のリストを指定の形式で出力する

    :param token:
    :param args:
    :return:
    """

    # APIからデータを取得
    items = get_items(token)
    # items = [
    #     {'title': 'aaa',
    #      'page_views_count': 11,
    #      'likes_count': 22,
    #      'stocks_count': 33,
    #      'id': 'hogehoge'},
    #     {'title': 'bbb',
    #      'page_views_count': 44,
    #      'likes_count': 55,
    #      'stocks_count': 66,
    #      'id': 'fugafuga'}
    # ]

    # リストをソートする
    sort_items(items, args.sort_by, args.reverse)

    # ファイル出力先のパスを決める
    if args.filename:
        # dockerで実行している場合はファイルの出力先を/tmpにする
        try:
            os.environ['IS_DOCKER']
            # フルパスが与えられた場合はファイル名だけにする
            filename = os.path.basename(args.filename)
            filepath = os.path.join('/tmp', filename)
        except KeyError:
            filepath = args.filename
    else:
        filepath = None

    # 結果を出力する
    if args.output == 'csv':
        output_csv(items, filepath)
    elif args.output == 'json':
        output_json(items, filepath)
    else:
        output_text(items, filepath)


def output_item_detail(token, item_id):
    """記事の詳細を出力する。

    :param token:
    :param item_id:
    :return:
    """

    # APIからデータを取得
    item = get_item_detail(token, item_id)

    # サマリーの表示
    print('Summary:')
    table = prettytable.PrettyTable()
    table.field_names = ['Title', 'Views', 'Likes', 'Stocks', 'Id']
    table.align['Title'] = 'l'
    table.align['Views'] = 'r'
    table.align['Likes'] = 'r'
    table.align['Stocks'] = 'r'
    table.align['Id'] = 'l'
    table.add_row([item['title'],
                   item['page_views_count'],
                   item['likes_count'],
                   item['stocks_count'],
                   item['id']])
    print(table)

    # いいねしたユーザーの表示
    print('Likers:')
    likers_table = prettytable.PrettyTable()
    likers_table.field_names = ['Id', 'Name']
    likers_table.align['Id'] = 'l'
    likers_table.align['Name'] = 'l'
    for liker in item['likers']:
        likers_table.add_row([liker['id'], liker['name']])
    print(likers_table)

    # ストックしたしたユーザーの表示
    print('Stockers:')
    stockers_table = prettytable.PrettyTable()
    stockers_table.field_names = ['Id', 'Name']
    stockers_table.align['Id'] = 'l'
    stockers_table.align['Name'] = 'l'
    for stocker in item['stockers']:
        stockers_table.add_row([stocker['id'], stocker['name']])
    print(stockers_table)


def main():

    # コマンド引数の処理
    parser = argparse.ArgumentParser(description='Qiitaのビュー数、いいね数、ストック数を取得します。',
                                     epilog='環境変数QIITA_TOKENにアクセストークンをセットしてから実行してください。')
    parser.add_argument('-o', '--output',
                        default='text',
                        action='store',
                        type=str,
                        choices=['text', 'csv', 'json'],
                        help='出力形式を指定します')
    parser.add_argument('-f', '--filename',
                        action='store',
                        type=str,
                        help='出力先のファイル名を指定します')
    parser.add_argument('--sort-by',
                        action='store',
                        type=str,
                        choices=['views', 'likes', 'stocks'],
                        help='結果を指定のキーでソートします')
    parser.add_argument('--reverse',
                        action='store_true',
                        help='ソートを降順にします')
    parser.add_argument('--item-id',
                        action='store',
                        type=str,
                        help='記事の詳細を表示します')
    args = parser.parse_args()

    token = os.environ['QIITA_TOKEN']

    if args.item_id:
        output_item_detail(token, args.item_id)
    else:
        output_items(token, args)


if __name__ == '__main__':
    main()
