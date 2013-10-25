# -*- coding: iso-8859-1 -*-

import urllib2
import re
import cookielib
import os
import sys
import time
import datetime
import threading
import BeautifulSoup

# Enable Eclipse debugger
REMOTE_DBG = False

# append pydev remote debugger
if REMOTE_DBG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    try:
        import pysrc.pydevd as pydevd
        # stdoutToServer and stderrToServer redirect stdout and stderr to
        # eclipse console
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
    except ImportError:
        sys.stderr.write("Error: " +
                         "You must add org.python.pydev.debug.pysrc " +
                         "to your PYTHONPATH.")
        sys.exit(1)
# try:
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import simplejson
__settings__ = xbmcaddon.Addon(id='plugin.video.elisa.viihde')
__language__ = __settings__.getLocalizedString
BASE_RESOURCE_PATH = xbmc.translatePath(
    os.path.join(__settings__.getAddonInfo('path'), "resources"))
sys.path.append(os.path.join(BASE_RESOURCE_PATH, "lib"))
vkopaivat = {0: __language__(30006), 1: __language__(30007),
             2: __language__(30008), 3: __language__(30009),
             4: __language__(30010), 5: __language__(30011),
             6: __language__(30012)}
# except ImportError:
#    pass

# Elisa Viihde

time_format = "%d.%m.%Y %H:%M:%S"


data_list = {}


if __settings__.getSetting("enable_cache") == 'true':
    # common cache service
    try:
        import StorageServer
    except:
        import storageserverdummy as StorageServer
    # (Your plugin name, Cache time in hours)
    cache = StorageServer.StorageServer("elisaplugin", 86400)


if __settings__.getSetting("enable_threads") == 'true':
    class UpdateProgramDataThread(threading.Thread):

        def __init__(self, cnt, row, print_star, date_string, totalItems):
            self.row = row
            self.print_star = print_star
            self.date_string = date_string
            self.totalItems = totalItems
            self.cnt = cnt

            super(UpdateProgramDataThread, self).__init__()

        def run(self):
            get_test(self.row['program_id'],
                     self.cnt, self.row, self.print_star,
                     self.date_string, self.totalItems)
            print 'ready: ' + str(self.cnt)


def get_login_url(username, password):
    return "http://elisaviihde.fi/etvrecorder/login.sl?username=" + \
        username + "&password=" + password + "&savelogin=true&ajax=true"

# logging in


def login(username=None, password=None):
    if 'xbmc' in globals():
        url = 'special://profile/addon_data/' + \
              'plugin.video.elisa.viihde/cookies.lwp'
        COOKIEFILE = xbmc.translatePath(url)
    else:
        COOKIEFILE = ''
    if username is None:
        username = __settings__.getSetting("username")
    if password is None:
        password = __settings__.getSetting("password")

    urlopen = urllib2.urlopen
    # This is a subclass of FileCookieJar that has useful load and save methods
    cj = cookielib.LWPCookieJar()
    Request = urllib2.Request

    if os.path.isfile(COOKIEFILE):
        cj.load(COOKIEFILE)

    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    urllib2.install_opener(opener)

    txdata = None
    txheaders = {
        'User-agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}

    login_url = get_login_url(username, password)
    req = Request(login_url, txdata, txheaders)
    urlopen(req)

    if COOKIEFILE:
        cj.save(COOKIEFILE)


def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
    return param


def add_search():
    u = sys.argv[0] + "?search=" + str('tiededo')
    print "Search: " + u
    liz = xbmcgui.ListItem(
        label=__language__(30017), iconImage="DefaultFolder.png")
    xbmcplugin.addDirectoryItem(
        handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return liz


def parse_datetime(dtstring, format="%d.%m.%Y %H:%M"):
    """
    Parse a datetime object from datetime string.

    @param dtstring: The datetime string
    @param format: excepted format of parse string
    e.g. 'Su 05.05.2012 12:00'
    """
    parts = dtstring.split(' ')
    if len(parts) > 2:
        dtstring = ' '.join(parts[-2:])
    parsestr = time.strptime
    print "DATETIME parsing %s, %s" % (dtstring, format)
    parsed_time = parsestr(dtstring, format)
    return datetime.datetime.fromtimestamp(time.mktime(parsed_time))


def parse_program_id(program_url_str):
    """
    parse the program id from the url string
    """
    return program_url_str.split('=')[1]


def search_items(qstr):
    print "search_items: " + qstr
    prog_url = "http://elisaviihde.fi/etvrecorder/search.sl?q=" + str(qstr)
    req = urllib2.Request(prog_url)
    response = urllib2.urlopen(req)
    search_html = response.read()
    search_html = fix_chars(search_html)
    # parse the search data from html
    search_data = BeautifulSoup.BeautifulSoup(search_html)
    rows = []
    existingh3 = search_data.find('h3', {'class': 'recordings_exist'})
    if existingh3:
        rtable = existingh3.findNextSibling(
            'table', {'class': 'recordings_table'})
        for row in rtable.findAll('tr'):
            tds = row.findAll('td')
            link_td = tds[2].a
            channel_td = tds[3]
            time_td = tds[4]
            stime = parse_datetime(time_td.text)
            drow = {'name': link_td.text,
                    'desc':
                    link_td['title'],
                    'url':
                    link_td['href'],
                    'channel':
                    channel_td.text,
                    'start_time':
                    stime.strftime(time_format),
                    'program_id':
                    parse_program_id(link_td['href'])
                    }
            rows.append(drow)
    return rows


def show_search_items(qstr):
    print "search_items: " + qstr
    items = search_items(qstr)
    for item in items:
        name = create_name(item)
        # link = add_watch_link(name,
        #                      item['program_id'],
        #                      totalItems=len(items),
        #                      )
        if __settings__.getSetting("thumbnails"):
            add_watch_link(name,
                           item['program_id'],
                           totalItems=len(items),
                           # playcount=row['viewcount'],
                           # duration=row['length'],
                           # date=date_name,
                           tn='',
                           aired=item['start_time'],
                           # episode=1,
                           plotoutline=item['desc'],
                           plot=item['channel'] + '\n' +
                           item['start_time'] + '\n' +
                           '\n' +
                           item['desc']
                           )
        else:
            add_watch_link(
                name,
                item['program_id'],
                totalItems=len(items),
                # playcount=row['viewcount'],
                # duration=row['length'],
                # date=date_name,
                tn='',
                aired=item['start_time'],
                # episode=1,
                plotoutline=item['desc'],
                plot=item['channel'] + '\n' +
                item['start_time'] + '\n' +
                '\n' +
                item['desc']
            )


def add_dir(name, id, iconimage):
    u = sys.argv[0] + "?id=" + str(id)
    liz = xbmcgui.ListItem(
        label=name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo('video', {"Title": name})
    xbmcplugin.addDirectoryItem(
        handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return liz


def add_watch_link(name, progid, totalItems=None, **data):
    u = sys.argv[0] + "?watch=true&progid=" + str(progid)
    liz = xbmcgui.ListItem(name)
    data['Title'] = name
    if data.get('tn'):
        liz.setThumbnailImage(data['tn'])
    liz.setInfo('video', data)
    xbmcplugin.addDirectoryItem(
        handle=int(sys.argv[1]), url=u, listitem=liz, totalItems=totalItems)
    return liz


def get_prog_data(prog_id):
    prog_url = "http://elisaviihde.fi/etvrecorder/program.sl?programid=" + \
        str(prog_id) + "&ajax"
    req = urllib2.Request(prog_url)
    response = urllib2.urlopen(req)
    link = response.read()
    link = fix_chars(link)
    prog_data = simplejson.loads(link)
    return prog_data


def get_test(prog_id, cnt, row, print_star, date_string, totalItems):
    prog_data = get_prog_data(prog_id)
    name = print_star + row['name']
    data_list[cnt] = [prog_data, row, name, date_string, totalItems]
    # print data_list
    return prog_data


def create_name(prog_data):
    parsed_time = time.strptime(prog_data['start_time'], time_format)
    weekday_numb = int(time.strftime("%w", parsed_time))
    prog_date = datetime.date.fromtimestamp(time.mktime(parsed_time))
    today = datetime.date.today()
    diff = today - prog_date
    if diff.days == 0:
        date_name = __language__(
            30013) + " " + time.strftime("%H:%M", parsed_time)
    elif diff.days == 1:
        date_name = __language__(
            30014) + " " + time.strftime("%H:%M", parsed_time)
    else:
        date_name = str(vkopaivat[weekday_numb]) + " " + time.strftime(
            "%d.%m.%Y %H:%M", parsed_time)
    return prog_data['name'] + " (" + prog_data['channel'] + \
        ", " + date_name + ")"


def watch_program(prog_id):
    prog_data = get_prog_data(prog_id)
    # print prog_data
    url = prog_data['url']
    name = create_name(prog_data)
    if prog_data['tn'] and __settings__.getSetting("thumbnails"):
        listitem = xbmcgui.ListItem(name, thumbnailImage=prog_data['tn'])
    else:
        listitem = xbmcgui.ListItem(name)
    listitem.setInfo('video', {'Title': name, 'plot': prog_data['short_text']})
    xbmc.Player().play(url, listitem)
    # mark program watched
    view_url = "http://elisaviihde.fi/etvrecorder/program.sl?programid=" + \
        str(prog_id) + "&view=true"
    urllib2.urlopen(view_url)
    return True


def fix_chars(string):
    string = string.replace("%20", " ")
    string = re.sub('%C3%A4', '\u00E4', string)
    string = re.sub('%C3%B6', '\u00F6', string)
    string = re.sub('%C3%A5', '\u00E5', string)
    string = re.sub('%C3%84', '\u00C4', string)
    string = re.sub('%C3%96', '\u00D6', string)
    string = re.sub('%C3%85', '\u00C5', string)
    string = re.sub('%2C', ',', string)
    string = re.sub('%26', '&', string)
    string = re.sub('%3F', '?', string)
    string = re.sub('%3A', ':', string)
    string = re.sub('%2F', '/', string)
    return string


def show_dir(id):

    if str(id) == "0":
        # show root directory
        folder_id = ""
        add_search()
    else:
        # show directory by id
        folder_id = str(id)

    folder_url = "http://elisaviihde.fi/etvrecorder/ready.sl?folderid=" + \
        folder_id + "&ajax"
    response = urllib2.urlopen(folder_url)
    link = response.read()
    link = fix_chars(link)

    response.close()

    data = simplejson.loads(link)
    data = data['ready_data']
    data = data.pop()
    totalItems = len(data['folders']) + len(data['recordings'])
    # list folders
    for row in data['folders']:
        name = row['name']
        id = row['id']
        add_dir(name, id, "")

    cnt = 0
    # list recordings
    progress = xbmcgui.DialogProgress()
    progress.create('Scraping record informations')
    for row in data['recordings']:
        cnt = cnt + 1
        if row['viewcount'] == "0":
            print_star = "* "
        else:
            print_star = ""

        parsed_time = time.strptime(
            row['timestamp'][: -5], "%Y-%m-%dT%H:%M:%S")
        weekday_numb = int(time.strftime("%w", parsed_time))

        #starttime = time.strftime("%d.%m %H:%M", parsed_time)

        prog_date = datetime.date.fromtimestamp(time.mktime(parsed_time))
        today = datetime.date.today()
        diff = today - prog_date
        if diff.days == 0:
            date_name = __language__(
                30013) + " " + time.strftime("%H:%M", parsed_time)
        elif diff.days == 1:
            date_name = __language__(
                30014) + " " + time.strftime("%H:%M", parsed_time)
        else:
            date_name = str(vkopaivat[weekday_numb]) + " " + time.strftime(
                "%d.%m.%Y %H:%M", parsed_time)
        #date_sort_name = time.strftime("%d.%m.%Y", parsed_time)
        date_string = time.strftime("%Y-%m-%d", parsed_time)

        if __settings__.getSetting("enable_threads") == 'true':

            while threading.active_count() > 50:
                print 'thread_max reached on ' + str(cnt)
                time.sleep(0.1)

            t = UpdateProgramDataThread(
                cnt, row, print_star, date_string, totalItems)
            t.start()
        else:
            if __settings__.getSetting("thumbnails"):
                if __settings__.getSetting("enable_cache"):
                    prog_data = cache.cacheFunction(
                        get_prog_data, row['program_id'])
                else:
                    prog_data = get_prog_data(row['program_id'])

                name = print_star + \
                    row['name'] + \
                    " (" + row['channel'] + ", " + date_name + ")"

                if not prog_data.get('tn'):
                    prog_data['tn'] = ''
                link = add_watch_link(name,
                                      row['program_id'],
                                      totalItems=totalItems,
                                      playcount=row['viewcount'],
                                      duration=row['length'],
                                      date=date_string,
                                      aired=date_string,
                                      tn=prog_data['tn'],
                                      episode=1,
                                      plotoutline=prog_data['short_text'],
                                      plot=row['channel'] + '\n' +
                                      row['start_time'] + '\n' +
                                      '\n' +
                                      prog_data['short_text']
                                      )
            else:
                name = print_star + \
                    row['name'] + \
                    " (" + row['channel'] + ", " + date_name + ")"
                link = add_watch_link(name,
                                      row['program_id'],
                                      totalItems=totalItems,
                                      playcount=row['viewcount'],
                                      duration=row['length'],
                                      date=date_string,
                                      aired=date_string,
                                      tn='',
                                      episode=1,
                                      plotoutline='',
                                      plot='')
        percent = int(100 - ((totalItems - cnt - 0.0) / totalItems * 100))
        progress.update(percent, row['name'])

        if progress.iscanceled():
            break
    progress.close()

    if data['recordings'] and __settings__.getSetting("enable_threads"):

        while threading.active_count() > 1:
            print 'waiting treads: ' + str(threading.active_count())
            # t.join()
            time.sleep(0.1)

        # for cnt, list in t.data_list.iteritems():
        print 'len: ' + str(len(data_list))
        keys = data_list.keys()
        keys.sort()
        for k in keys:
            prog_data = data_list[k][0]
            row = data_list[k][1]
            name = data_list[k][2]
            date_string = data_list[k][3]
            totalItems = data_list[k][4]
            if not prog_data.get('tn'):
                prog_data['tn'] = ''
            link = add_watch_link(name,
                                  row['program_id'],
                                  totalItems=totalItems,
                                  playcount=row['viewcount'],
                                  duration=row['length'],
                                  date=date_string,
                                  aired=date_string,
                                  tn=prog_data['tn'],
                                  episode=1,
                                  plotoutline=prog_data['short_text'],
                                  plot=row['channel'] + '\n' +
                                  row['start_time'] + '\n' +
                                  '\n' +
                                  prog_data['short_text']
                                  )
    else:
        # no records in folder
        pass


def mainloop():
    # check login
    username = __settings__.getSetting("username")
    password = __settings__.getSetting("password")
    response = urllib2.urlopen(get_login_url(username, password))
    link = response.read()

    if not str(link) == "TRUE":
        dialog = xbmcgui.Dialog()
        ok = dialog.ok('XBMC', __language__(30003), __language__(30004))
        if ok is True:
            __settings__.openSettings(url=sys.argv[0])

    else:
        login()
        params = get_params()

        # dialog = xbmcgui.Dialog()
        # ok = dialog.ok('XBMC', str(params))
        xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
        #xbmcplugin.setContent(int(sys.argv[1]), 'files')

        folder_id = None
        prog_id = None
        watch = None
        search = None
        try:
            folder_id = int(params["id"])
        except:
            pass

        try:
            prog_id = int(params["progid"])
        except:
            pass

        try:
            watch = str(params["watch"])
        except:
            pass

        try:
            search = str(params["search"])
            print "Searching for " + search
        except:
            pass

        if search is not None:
            keyboard = xbmc.Keyboard()
            keyboard.doModal()
            if (keyboard.isConfirmed()):
                show_search_items(str(keyboard.getText()))

        elif folder_id is None and prog_id is None:
            show_dir("0")
        elif prog_id is None and folder_id is not None:
            show_dir(str(folder_id))
        elif watch == "true" and prog_id is not None:
            watch_program(str(prog_id))
        else:
            show_dir("0")

    # Set view mode (C:\Program Files
    # (x86)\XBMC\addons\skin.confluence\720p\MyVideoNav.xml)
    xbmc.executebuiltin('Container.SetViewMode(504)')
    # xbmc.executebuiltin('Container.SetViewMode(51)')

    #xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
    # xbmc.executebuiltin("Container.Update")
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


if __name__ == '__main__':
    mainloop()
