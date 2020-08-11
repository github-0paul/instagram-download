from datetime import datetime, date
import instaloader
import json
import logging
import urllib.parse as parse
import os, random, time
import excel
import argparse
logging.basicConfig(format='%(asctime)s  %(filename)s : %(levelname)s  %(message)s',
                    datefmt='%Y-%m-%d %A %H:%M:%S',
                    level=logging.DEBUG)


def datetime_format(dt=None):
    if dt is None or not isinstance(dt, (datetime, date)):
        return ''

    return dt.strftime('%Y-%m-%d %H:%M:%S')


def get_current_path():
    return os.path.split(os.path.realpath(__file__))[0]


def load_pic(instaloader=None, filename='', post=None):
    downloaded = False
    if post.typename == 'GraphSidecar':
        edge_number = 1
        for sidecar_node in post.get_sidecar_nodes():
            # Download picture or video thumbnail
            if not sidecar_node.is_video or instaloader.download_video_thumbnails is True:
                downloaded &= instaloader.download_pic(filename=filename, url=sidecar_node.display_url,
                                                       mtime=post.date_local, filename_suffix=str(edge_number))

            # Additionally download video if available and desired
            if sidecar_node.is_video and instaloader.download_videos is True:
                downloaded &= instaloader.download_pic(filename=filename, url=sidecar_node.video_url,
                                                       mtime=post.date_local, filename_suffix=str(edge_number))
            edge_number += 1
    elif post.typename == 'GraphImage':
        downloaded = instaloader.download_pic(filename=filename, url=post.url, mtime=post.date_local)
    elif post.typename == 'GraphVideo':
        if instaloader.download_video_thumbnails is True:
            downloaded = instaloader.download_pic(filename=filename, url=post.url, mtime=post.date_local)
    else:
        instaloader.context.error("Warning: {0} has unknown typename: {1}".format(post, post.typename))

    return downloaded


def fetch_items(file_path):
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise FileNotFoundError('%s can not found' % file_path)

    with open(file=file_path, encoding="utf-8") as f:
        examples = f.readlines()
    items = []
    for item in examples:
        hashtag = item.strip().replace('#', '')
        items.append(hashtag)

    return items


def get_random_seconds(min=0.1, factor=1) :

    return min + (random.random() * factor)


class Download:

    def __init__(self,
                 data_file_name=None,
                 data_sheet_name=None,
                 data_titles=None,
                 post_file_name=None,
                 post_sheet_name=None,
                 post_titles=None,
                 top_k = None,
                 since_date = None,
                 until_date=None,
                 ins_username=None,
                 ins_password=None,
                 is_fetch_by_tag=False,
                 is_download_comments=False
                 ):
        self.data_file_name = data_file_name
        self.data_sheet_name = data_sheet_name
        self.data_titles = data_titles
        self.post_file_name = post_file_name
        self.post_sheet_name = post_sheet_name
        self.post_titles = post_titles
        self.top_k = top_k
        self.since_date = since_date
        self.until_date = until_date
        self.ins_username = ins_username
        self.ins_password = ins_password
        self.L = None
        self.is_fetch_by_tag = is_fetch_by_tag
        self.is_download_comments = is_download_comments

    def run_account(self, since, until, items_file_path):
        current_dir = get_current_path()
        today = datetime.today().strftime('%Y-%m-%d')

        items = fetch_items(items_file_path)
        self.create_instaloader()

        for member in items:
            try:
                full_dir_path = os.path.join(current_dir, 'download', 'account_data', member, '_'.join([since, until, today]))

                media_full_path, post_xls, acc_xls = self.create_xls(full_dir_path)

                profile = instaloader.Profile.from_username(self.L.context, username=member)
                acc_xls.write_excel_xls_append(sheet_name=self.data_sheet_name,
                                               value=[[profile.mediacount, profile.followers]])

                posts = profile.get_posts()
                self.handle_posts(self.L, posts, media_full_path, post_xls)

                sleep_time = get_random_seconds()
                logging.info('Sleep time: %f seconds' % sleep_time)
                time.sleep(sleep_time)
            except Exception as e:
                logging.exception(e)
        self.L.close()

    def handle_posts(self, L, posts, media_full_path, post_xls):
        post_count = 0
        # fetch all posts data
        post_cache_arr = []

        for post in posts:
            postdate = post.date
            if (not self.is_fetch_by_tag) and (postdate > self.until_date or postdate <= self.since_date):
                continue
            else:
                _media_name = os.path.basename(parse.urlparse(post.url).path)
                if self.is_download_comments:
                    _comments_list = json.dumps(list(post.get_comments()), ensure_ascii=False, default=datetime_format)
                else:
                    _comments_list = post.comments

                _hashtags = json.dumps(post.caption_hashtags, ensure_ascii=False)
                _date_format = datetime_format(post.date)
                _post = [_date_format, str(post.mediaid), _media_name, _comments_list, post.likes, _hashtags]
                load_pic(instaloader=L, filename=os.path.join(media_full_path, os.path.splitext(_media_name)[0]),
                         post=post)
                post_cache_arr.append(_post)

                if post_cache_arr.__len__() >= 5:
                    try:
                        post_xls.write_excel_xls_append(sheet_name=self.post_sheet_name, value=post_cache_arr)
                    except Exception as e:
                        logging.exception(e)

                    post_cache_arr.clear()

                post_count += 1
                if self.top_k is not None and post_count >= self.top_k:
                    break

            sleep_time = get_random_seconds()
            logging.info('Sleep time: %f seconds' % sleep_time)
            time.sleep(sleep_time)

        if post_cache_arr.__len__() >= 1:
            post_xls.write_excel_xls_append(sheet_name=self.post_sheet_name, value=post_cache_arr)
            post_cache_arr.clear()

    def create_instaloader(self):
        self.L = instaloader.Instaloader(
            compress_json=False,
            max_connection_attempts=3,
            request_timeout=10,
            quiet=True,
            commit_mode=False)
        self.L.login(user=self.ins_username, passwd=self.ins_password)

    def create_xls(self, full_dir_path):
        if not os.path.exists(full_dir_path):
            os.makedirs(full_dir_path)

        media_full_path = os.path.join(full_dir_path, 'images')
        if not os.path.exists(media_full_path):
            os.makedirs(media_full_path)

        # create account mate date file
        acc_xls = excel.xls_utls(dir=full_dir_path, file_name=self.data_file_name)
        acc_xls.create_sheet_with_titles(sheet_name=self.data_sheet_name, value=self.data_titles)
        # create account post date file
        post_xls = excel.xls_utls(dir=full_dir_path, file_name=self.post_file_name)
        post_xls.create_sheet_with_titles(sheet_name=self.post_sheet_name, value=self.post_titles)

        return media_full_path, post_xls, acc_xls

    def run_hashtag(self, items_file_path):
        current_dir = get_current_path()
        today = datetime.today().strftime('%Y-%m-%d')
        items = fetch_items(items_file_path)
        self.create_instaloader()
        for member in items:
            try:
                logging.info('Fetching hashtag: %s' % member)
                full_dir_path = os.path.join(current_dir, 'download', 'hashtag_data', member, today)
                media_full_path, post_xls, acc_xls = self.create_xls(full_dir_path)
                hashtag = instaloader.Hashtag.from_name(self.L.context, name=member)
                related_tags = []
                for ht in hashtag.get_related_tags():
                    related_tags.append(ht.name)


                json_hashtags = json.dumps(related_tags, ensure_ascii=False)
                acc_xls.write_excel_xls_append(sheet_name=self.data_sheet_name,
                                               value=[[hashtag.mediacount, json_hashtags]])

                posts = hashtag.get_top_posts()
                self.handle_posts(self.L, posts, media_full_path, post_xls)

                sleep_time = get_random_seconds()
                logging.info('Sleep time: %f seconds' % sleep_time)
                time.sleep(sleep_time)

            except Exception as e:
                logging.exception(e)
        self.L.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='manual to this script')
    parser.add_argument('--top-k', type=int, default=None, required=False, help='How many pieces of data are retrieved, or all if not specified')
    parser.add_argument('--since-date', type=str, required=False, default=None, help='Start date in format yyyy-MM-dd, if mode is account, it must be filled')
    parser.add_argument('--until-date', type=str, required=True, help='End date in format yyyy-MM-dd, if mode is account, it must be filled')
    parser.add_argument('--mode', type=str, default='account',
                        required=False, help='account | hashtag, The default is account')
    parser.add_argument('--items-file-path', type=str, required=False, default=None, help='File address, if not specified, go to res/accounts.txt or res/hashtags.txt in the directory of current file')
    parser.add_argument('--ins-username', type=str, required=True, help='The username of instagram')
    parser.add_argument('--ins-password', type=str, required=True, help='The password of instagram')
    parser.add_argument('--download-comments', type=bool, default=False, required=False, help='Do you want to download reviews? The default is false')
    args = parser.parse_args()
    logging.info('Args: %s', args)

    if 'account' == args.mode:
        items_file_path = args.items_file_path
        if items_file_path is None:
            items_file_path = os.path.join(get_current_path(),'res', 'accounts.txt')
        if args.since_date is None:
            raise AttributeError('since-date must be filled')
        if args.until_date is None:
            raise AttributeError('since-date must be filled')
        since = datetime.strptime(args.since_date, '%Y-%m-%d')
        until = datetime.strptime(args.until_date, '%Y-%m-%d')

        download=Download(
            data_file_name='account_mate_data.xls',
            data_sheet_name='account_mate_data',
            data_titles=[["posts", "followers"]],
            post_file_name='post_data.xls',
            post_sheet_name='account_posts',
            post_titles=[["timestamp", "post_id","image_name","comments", "likes","hashtags"]],
            top_k=args.top_k,
            since_date=since,
            until_date=until,
            ins_username=args.ins_username,
            ins_password=args.ins_password,
            is_download_comments=args.download_comments
        )
        download.run_account(args.since_date, args.until_date, items_file_path)
    elif 'hashtag' == args.mode:
        items_file_path = args.items_file_path
        if items_file_path is None:
            items_file_path = os.path.join(get_current_path(),'res', 'hashtags.txt')

        download = Download(
            data_file_name='hashtag_mate_data.xls',
            data_sheet_name='hashtag_mate_data',
            data_titles=[["number of posts", "ralated hashtags"]],
            post_file_name='top_n_post_data.xls',
            post_sheet_name='top_n_post_data',
            post_titles=[["timestamp", "post_id", "image_name", "comments", "likes", "hashtags"]],
            top_k=args.top_k,
            since_date=None,
            until_date=None,
            ins_username=args.ins_username,
            ins_password=args.ins_password,
            is_fetch_by_tag=True,
            is_download_comments=args.download_comments
        )
        download.run_hashtag(items_file_path)
    else:
        logging.error('The mode `%s` can not find', args.mode)

