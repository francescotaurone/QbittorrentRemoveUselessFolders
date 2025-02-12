import requests
import time
import os
import shutil

URL = ""
USERNAME = ""
PASSWORD = ""
PATH_TO_SCAN = ""

def scanRecurse(baseDir):
    for entry in os.scandir(baseDir):
        if entry.is_file():
            yield baseDir
        else:
            yield from scanRecurse(entry.path)
class Torrent(object):
    def __init__(self):
        # Proper attributes:
        # hash, name, category, tracker, status, size, ratio, uploaded, create_time, seeding_time
        # NOTE: The attribute 'last_activity' stores the time interval since last activity,
        #       not the unix timestamp of last activity.
        pass


class qBittorrent(object):

    # API Handler for v2
    class qBittorrentAPIHandlerV2(object):
        def __init__(self, host):
            # Host
            self._host = host
            # Requests Session
            self._session = requests.Session()

        # Check API Compatibility
        def check_compatibility(self):
            request = self._session.get(self._host + "/api/v2/app/webapiVersion")
            return request.status_code != 404  # compatible if API exsits

        # Login
        def login(self, username, password):
            return self._session.post(
                self._host + "/api/v2/auth/login",
                data={"username": username, "password": password},
            )
          
        # Get torrent list
        def torrent_list(self):
            return self._session.get(self._host + "/api/v2/torrents/info")

        # Get torrent categories
        def torrent_categories(self):
            return self._session.get(self._host + "/api/v2/torrents/categories")

        # Get torrent's generic properties
        def torrent_generic_properties(self, torrent_hash):
            return self._session.get(
                self._host + "/api/v2/torrents/properties",
                params={"hash": torrent_hash},
            )
          
    def __init__(self, host):
        # Logger

        # Torrents list cache
        self._torrents_list_cache = []
        self._refresh_cycle = 30
        self._refresh_time = 0

        # Request Handler
        self._request_handler = None
        for obj in [self.qBittorrentAPIHandlerV2]:  # New version API first
            handler = obj(host)
            if handler.check_compatibility():
                self._request_handler = handler
                break
        if self._request_handler is None:
            raise Exception("No compatible API found")

    # Login to qBittorrent
    def login(self, username, password):
        try:
            request = self._request_handler.login(username, password)
        except Exception as exc:
            raise Exception(str(exc))

        if request.status_code == 200:
            if request.text == "Fails.":  # Fail
                raise Exception(request.text)
        else:
            raise Exception("The server returned HTTP %d." % request.status_code)

    # Get Torrents List folder names
    def torrents_list_involved_paths(self):
        # Request torrents list
        torrent_involved_paths = []
        request = self._request_handler.torrent_list()
        result = request.json()
        # Save to cache
        self._torrents_list_cache = result
        self._refresh_time = time.time()
        # Get hash for each torrent
        for torrent in result:
            torrent_involved_paths.append(torrent["content_path"])
            torrent_involved_paths.append(torrent["download_path"])
            torrent_involved_paths.append(torrent["root_path"])
            torrent_involved_paths.append(torrent["save_path"])
            torrent_involved_paths.append(torrent["save_path"] + torrent["name"])
        return set(torrent_involved_paths)

    # Get Torrents List names
    def torrents_list_names(self):
        # Request torrents list
        torrent_names = []
        request = self._request_handler.torrent_list()
        result = request.json()
        # Save to cache
        self._torrents_list_cache = result
        self._refresh_time = time.time()
        # Get hash for each torrent
        for torrent in result:

            torrent_names.append(torrent["name"])
        return set(torrent_names)

    def torrents_list_categories_paths(self):
        request = self._request_handler.torrent_categories()
        result = request.json()
        return set([cat["savePath"] for cat in result.values()])


if __name__ == "__main__":
    # qBittorrent
    print("Starting check for useless folders")
    qb = qBittorrent(URL)
    qb.login(USERNAME, PASSWORD)
    paths_involved_in_current_torrents = qb.torrents_list_involved_paths()
    paths_for_categories = qb.torrents_list_categories_paths()
    subfolders = list(scanRecurse(PATH_TO_SCAN))
    paths_to_remove_candidates = (
        set(subfolders)
        - paths_involved_in_current_torrents
        - paths_for_categories
    )
    torrent_names = list(qb.torrents_list_names())
    paths_to_remove = set()
    for path in paths_to_remove_candidates:
        if any([name in path for name in torrent_names]):
            continue
        paths_to_remove.add(path)
    for path in paths_to_remove:
        print("Removing path "+path)
        try:
            shutil.rmtree(path)
        except Exception as e:
            print(e)
