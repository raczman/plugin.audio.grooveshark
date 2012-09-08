import sys, pickle
import xbmcplugin, xbmcgui, xbmcaddon
from datetime import *

resources = xbmc.translatePath(os.path.join(xbmcaddon.Addon('plugins.audio.grooveshark').getAddonInfo('path'), 'resources', 'lib' ))
sys.path.append(resources)
import grooveshark as g

__addon__     = xbmcaddon.Addon('plugin.audio.groove')
__addonname__ = __addon__.getAddonInfo('name')
__cwd__       = __addon__.getAddonInfo('path')
__author__    = __addon__.getAddonInfo('author')
__version__   = __addon__.getAddonInfo('version')
__language__  = __addon__.getLocalizedString
__debugging__  = __addon__.getSetting('debug')

handle = int(sys.argv[1])
cacheDir = os.path.join(xbmc.translatePath('special://masterprofile/addon_data/'), os.path.basename(__cwd__))
settings = xbmcaddon.Addon(id='plugin.audio.grooveshark')

MODE_LIBRARY = 1
MODE_FAVOURITES = 2
MODE_ARTISTS = 3
MODE_ALBUMS = 4
MODE_ARTISTS_ALBUMS = 5
MODE_ALBUMS_SONGS = 6
MODE_PLAY_SONG = 7
MODE_SEARCH_ALBUMS = 8

class GUI(object):
    def add_dir(self, name, mode, id, url='', extra={}, img=''):
        if url == '':
            url = sys.argv[0]+'?mode='+str(mode)+'&id='+str(id)
            for key, item in extra.items():
                url += '&%s=%s' % (key, item)
        xbmcplugin.addDirectoryItem(handle,url,xbmcgui.ListItem(name,name,img),True)

    def song_listitem(self, song):
        track = 0
        try: track = int(song.track)
        except: pass
        item = xbmcgui.ListItem(label=song.name, thumbnailImage=song._cover_url, iconImage=song._cover_url)
        item.setInfo('music', infoLabels={"title":song.name, 
                                            "album":song.album.name, 
                                            'duration':float(song.duration),
                                            'artist':song.artist.name,
                                            'tracknumber':track})
        item.setProperty('IsPlayable','true')
        item.setProperty('mimetype','audio/mpeg')
        item.setProperty('stream', song.stream.url)
        return item
        
    def add_song(self, song, mode, id, extra={}):
        url = sys.argv[0]+'?mode='+str(mode)+'&id='+str(id)
        for key, item in extra.items():
            url += '&%s=%s' % (key, item)
        item = self.song_listitem(song)
        xbmcplugin.addDirectoryItem(handle, song.stream.url, item, False)
        
    def get_user_input(self, heading="", default=""):
        k = xbmc.Keyboard(default, heading, False)
        k.doModal()
        if k.isConfirmed():
            return unicode(k.getText(), 'utf-8')
        return ''
        
gui = GUI()
        
class Grooveshark(object):
    
    def __init__(self):
        print 'login'
        if os.path.isdir(cacheDir) == False:
            os.makedirs(cacheDir)
            
    def login(self):
        self.client = g.Client()
        self.client.init()
        info, res = self.client.connection.request('authenticateUser',
                                            {'password':settings.getSetting('pass'),
                                            'username':settings.getSetting('login'),'savePassword':0},
                                            self.client.connection.header('authenticateUser'))
        self.userid = int(res['userID'])
 
    def grab_library(self):
        self.login()
        info, res = self.client.connection.request('userGetSongsInLibrary',
                                                    {'userID':self.userid,'page':0},
                                                    self.client.connection.header('userGetSongsInLibrary'))
        songs = []
        songs.extend(res['Songs'])
        page = 0
        while res['hasMore'] == True:
            page += 1
            info, res = self.client.connection.request('userGetSongsInLibrary',
                                                        {'userID':self.userid,'page':page},
                                                        self.client.connection.header('userGetSongsInLibrary'))
            songs.extend(res['Songs'])
            
        artists = []
        albums = []
        for s in songs:
            a = {'id':s['ArtistID'],'name':s['ArtistName']}
            b = {'id':s['AlbumID'],'name':s['AlbumName'],'artist_id':int(s['ArtistID'])}
            if a not in artists:
                artists.append(a)
            if b not in albums:
                albums.append(b)
            for key, item in s.items():
                if s[key] == 'None':
                    s[key] = '0'
                s[key] = unicode(item)
                
        self.write_cache('songs', songs)
        self.write_cache('albums', albums)
        self.write_cache('artists', artists)
        
    def write_cache(self, name, obj):
        path = os.path.join(cacheDir, name)
        exp_path = os.path.join(cacheDir, name+'.exp')
        f = open(path, 'wb')
        pickle.dump(obj, f)
        f.close()
        f = open(exp_path, 'wb')
        pickle.dump(datetime.now(), f)
        f.close()
        
    def get_cache_age(self, name):
        path = os.path.join(cacheDir, name+'.exp')
        f = open(path, 'rb')
        exp = pickle.load(f)
        f.close()
        return (datetime.now() - exp).seconds / 60
        
    def load_cache(self, name):
        path = os.path.join(cacheDir, name)
        f = open(path, 'rb')
        ret = pickle.load(f)
        f.close()
        return ret
        
    def get_song_from_cache(self, id):
        songs = self.load_cache('songs')
        for s in songs:
            if s['SongID'] == unicode(id):
                return s
        return None
        
    def main_menu(self):
        gui.add_dir('My Library', MODE_LIBRARY, 0)
        gui.add_dir('Favourites', MODE_FAVOURITES, 0)
        gui.add_dir('Search Songs', MODE_SEARCH_ALBUMS, 0)
        
    def library(self, page):
        if self.get_cache_age('songs') > int(settings.getSetting('cachetime')):
            self.grab_library()
        gui.add_dir('Artists', MODE_ARTISTS, 0)
        gui.add_dir('Albums', MODE_ALBUMS, 0)

    def artists(self, page):
        artists = self.load_cache('artists')
        items = sorted(artists, key=lambda x: x['name'])
        for i in items:
            gui.add_dir(i['name'], MODE_ARTISTS_ALBUMS, i['id'], img="http://images.grooveshark.com/static/artists/500_"+i['id']+".jpg") 
    
    def artists_albums(self, artist):
        albums = self.load_cache('albums')
        items = sorted([x for x in albums if x['artist_id'] == artist], key=lambda x: x['name'])
        for i in items:
            gui.add_dir(i['name'], MODE_ALBUMS_SONGS, i['id'], img="http://images.grooveshark.com/static/albums/500_"+i['id']+".jpg") 
    
    def album_songs(self, album):
        self.login()
        songs = self.load_cache('songs')
        items = sorted([x for x in songs if x['AlbumID'] == unicode(album)], key=lambda x: x['TrackNum'])
        for i in items:
            song = g.Song.from_response(i, self.client.connection)
            gui.add_song(song, MODE_PLAY_SONG, song.id)
            
    def play_song(self, id):
        self.login()
        song = self.get_song_from_cache(id)
        song = g.Song.from_response(i, self.client.connection)
        song = gui.song_listitem(song)
            
    def albums(self):
        albums = self.load_cache('albums')
        items = sorted(albums, key=lambda x: x['name'])
        for i in items:
            gui.add_dir(i['name'], MODE_ALBUMS_SONGS, i['id'], img='http://images.grooveshark.com/static/albums/500_'+i['id']+".jpg")
            
    def search_songs(self):
        query = gui.get_user_input('Query')
        self.login()
        for s in self.client.search(query, 'Albums'):
            gui.add_dir(s, MODE_PLAY_SONG, s.id)
            
addon = Grooveshark()
    
def getparams():
    """
    Pick up parameters sent in via command line
    @return dict list of parameters
    @thanks Team XBM  - I lifted this straight out of the shoutcast addon
    """
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
        params=sys.argv[2]
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]
    return param
    
params = getparams()
mode = None
id = 0
try: mode = int(params["mode"])
except: pass
try: id = int(params["id"])
except: pass

if mode == None:
    addon.main_menu()
elif mode == MODE_LIBRARY:
    addon.library(id)
elif mode == MODE_ARTISTS:
    addon.artists(id)
elif mode == MODE_ALBUMS:
    addon.albums()
if mode == MODE_ARTISTS_ALBUMS:
    addon.artists_albums(id)
if mode == MODE_ALBUMS_SONGS:
    addon.album_songs(id)
if mode == MODE_SEARCH_ALBUMS:
    addon.search_albums()

if mode != MODE_PLAY_SONG:
    xbmcplugin.endOfDirectory(handle)