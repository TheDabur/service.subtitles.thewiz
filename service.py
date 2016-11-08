from os import path
from requests import get
from json import loads, load
from shutil import copyfileobj, rmtree
from time import time
from unicodedata import normalize
from urllib import urlretrieve, unquote_plus, unquote, urlopen, quote
from xbmcaddon import Addon
from xbmcplugin import endOfDirectory, addDirectoryItem
from xbmcgui import ListItem, Dialog
from xbmcvfs import listdir, exists, mkdirs
from xbmc import translatePath, executebuiltin, getInfoLabel, executeJSONRPC, Player, sleep
from re import sub
import sys  
reload(sys)  
sys.setdefaultencoding('utf8')

__addon__ = Addon()
__scriptid__ = __addon__.getAddonInfo('id')
__version__ = __addon__.getAddonInfo('version')
__temp__ = unicode(translatePath(__addon__.getAddonInfo('profile')), 'utf-8')
__subs__ = unicode(translatePath(path.join(__temp__, 'subs')), 'utf-8')

def convert_to_utf(file):
	try:
		with codecs.open(file, "r", "cp1255") as f:
			srt_data = f.read()

		with codecs.open(file, 'w', 'utf-8') as output:
			output.write(srt_data)
	except: pass

def normalizeString(str):
    return normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('utf-8', 'ignore')
	
def download(id):
	try:
		rmtree(__subs__)
	except: pass
	mkdirs(__subs__)
	subtitle_list = []
	exts = [".srt", ".sub"]
	archive_file = path.join(__temp__, 'thewiz.sub.'+id+'.zip')
	if not path.exists(archive_file):
		urlretrieve("http://subs.thewiz.info/zip/"+id+".zip", archive_file)
	executebuiltin(('XBMC.Extract("%s","%s")' % (archive_file, __subs__)).encode('utf-8'), True)
	for file_ in listdir(__subs__)[1]:
		ufile = file_.decode('utf-8')
		file_ = path.join(__subs__, ufile)
		if path.splitext(ufile)[1] in exts:
			convert_to_utf(file_)
			subtitle_list.append(file_)
	return subtitle_list

def getParams(arg):
	param=[]
	paramstring=arg
	if len(paramstring)>=2:
		params=arg
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

def getParam(name,params):
	try:
		return unquote_plus(params[name])
	except:	pass

def GetJson(imdb,tvdb=0,season=0,episode=0):
	if imdb:
		filename = 'thewiz.imdb.%s.%s.%s.json'%(imdb,season,episode)
		url = "http://subs.thewiz.info/get.php?imdb=%s&season=%s&episode=%s"%(imdb,season,episode)
	elif tvdb:
		filename = 'thewiz.tvdb.%s.%s.%s.json'%(imdb,season,episode)
		url = "http://subs.thewiz.info/get.php?tvdb=%s&season=%s&episode=%s"%(tvdb,season,episode)
	Caching(filename,url)
	json_file = path.join(__temp__, filename)
	if path.exists(json_file) and path.getsize(json_file)>20:
		subs_rate = []
		with open(json_file) as json_data:
			json_object = load(json_data)
		for item_data in json_object:
			subtitle_rate = _calc_rating(item_data["versioname"])
			subs_rate.append({"versioname":item_data["versioname"],
				"id": item_data["id"],"sync": subtitle_rate >= 3.8})
		subs_rate = sorted(subs_rate, key=lambda x: (x['sync']), reverse=True)

		for item_data in subs_rate:
			listitem = ListItem(label= "Hebrew",label2= item_data["versioname"],thumbnailImage="he")
			if item_data["sync"]:
				listitem.setProperty("sync", "true")
			url = "plugin://%s/?action=download&versioname=%s&id=%s" % (__scriptid__, item_data["versioname"], item_data["id"])
			addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)


def _calc_rating(subsfile):
	file_original_path = unquote(unicode(Player().getPlayingFile(), 'utf-8'))
	file_name = path.basename(file_original_path)
	folder_name = path.split(path.dirname(file_original_path))[-1]

	subsfile = sub(r'\W+', '.', subsfile).lower()
	file_name = sub(r'\W+', '.', file_name).lower()
	folder_name = sub(r'\W+', '.', folder_name).lower()

	subsfile = subsfile.split('.')
	file_name = file_name.split('.')[:-1]
	folder_name = folder_name.split('.')

	if len(file_name) > len(folder_name):
		diff_file = list(set(file_name) - set(subsfile))
		rating = (1 - (len(diff_file) / float(len(file_name)))) * 5
	else:
		diff_folder = list(set(folder_name) - set(subsfile))
		rating = (1 - (len(diff_folder) / float(len(folder_name)))) * 5

	return round(rating, 1)

def SearchMovie(query,year):
	filename = 'thewiz.search.movie.%s.%s.json'%(normalizeString(query),year)
	if year>0:
		url = "http://api.tmdb.org/3/search/movie?api_key=f7f51775877e0bb6703520952b3c7840&query=%s&year=%s&language=he"%(quote(query),year)
	else:
		url = "http://api.tmdb.org/3/search/movie?api_key=f7f51775877e0bb6703520952b3c7840&query=%s&language=he"%(quote(query))
	json = Caching(filename,url)
	try:
		tmdb_id = int(json["results"][0]["id"])
	except:
		return 0
		pass
	filename = 'thewiz.tmdb.%s.json'%(tmdb_id)
	url = "http://api.tmdb.org/3/movie/%s?api_key=f7f51775877e0bb6703520952b3c7840&language=en"%(tmdb_id)
	json = Caching(filename,url)
	try:
		imdb_id = json["imdb_id"]
	except:
		return 0
		pass
	return imdb_id

def Caching(filename,url):
	json_file = path.join(__temp__, filename)
	if not path.exists(json_file) or not path.getsize(json_file)>20 or (time()-path.getmtime(json_file)>60*60*24):
		urlretrieve(url, json_file)
	if path.exists(json_file) and path.getsize(json_file)>20:
		with open(json_file) as json_data:
			json_object = load(json_data)
		return json_object
	else:
		return 0

def ManualSearch(title):
	filename = 'thewiz.search.filename.%s.json'%(quote(title))
	url = "http://subs.thewiz.info/get.php?filename=%s"%(normalizeString(title))
	try:
		json = Caching(filename,url)
		if json["type"]=="episode":
			tvdb_id = urlopen("http://subs.thewiz.info/api.tvdb.php?name="+quote(json['title'])).read()
			if tvdb_id<>'' and tvdb_id>100:
				GetJson(0,str(tvdb_id),json['season'],json['episode'])
		elif json["type"]=="movie":
			if "year" in json:
				imdb_id = SearchMovie(str(json['title']),json['year'])
			else:
				imdb_id = SearchMovie(str(json['title']),0)
			if imdb_id:
				GetJson(imdb_id,0,0,0)
	except:	pass

if not exists(__temp__):
	mkdirs(__temp__)

action=None
if len(sys.argv) >= 2:   
	params = getParams(sys.argv[2])
	action = getParam("action", params)

if action=='search':
	item = {}
	item['year'] = getInfoLabel("VideoPlayer.Year")  # Year

	item['season'] = str(getInfoLabel("VideoPlayer.Season"))  # Season
	if item['season']=='' or item['season']<1:
		item['season'] = 0
	item['episode'] = str(getInfoLabel("VideoPlayer.Episode"))  # Episode
	if item['episode']=='' or item['episode']<1:
		item['episode'] = 0

	if item['episode']==0:
		item['title'] = normalizeString(getInfoLabel("VideoPlayer.Title"))  # no original title, get just Title
	else:	
		item['title'] = normalizeString(getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
	if item['title'] == "":
		item['title'] = normalizeString(getInfoLabel("VideoPlayer.OriginalTitle"))  # try to get original title

	imdb_id = 0
	tvdb_id = 0
	try:
		playerid_query = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
		playerid = loads(executeJSONRPC(playerid_query))['result'][0]['playerid']
		imdb_id_query = '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": {"playerid": ' + str(playerid) + ', "properties": ["imdbnumber"]}, "id": 1}'
		imdb_id = loads(executeJSONRPC (imdb_id_query))['result']['item']['imdbnumber']
	except:	pass
	if imdb_id[:2]=="tt":	#Simple IMDB_ID
		GetJson(imdb_id,0,item['season'],item['episode'])
	else:
		# Search TV Show by Title
		if item['season'] != 0 or item['episode'] != 0:
			try:
				tvdb_id = urlopen("http://subs.thewiz.info/api.tvdb.php?name="+quote(item['title'])).read()
				if tvdb_id<>'' and tvdb_id>100:
					GetJson(0,str(tvdb_id),item['season'],item['episode'])
			except:	pass
		# Search Movie by Title+Year
		else:
			try:
				imdb_id = SearchMovie(query=item['title'],year=item['year'])
				if not imdb_id[:2]=="tt":
					imdb_id = SearchMovie(query=item['title'],year=(int(item['year'])-1))
				if imdb_id[:2]=="tt":
					GetJson(imdb_id,0,0,0)
			except:	pass
	# Search Local File
	if not imdb_id and not tvdb_id:
		ManualSearch(item['title'])
	endOfDirectory(int(sys.argv[1]))
	if __addon__.getSetting("Debug") == "true":
		if imdb_id[:2]=="tt":
			Dialog().ok("Debug "+__version__,str(item),"imdb: "+str(imdb_id))
		elif tvdb_id>0:
			Dialog().ok("Debug "+__version__,str(item),"tvdb: "+str(tvdb_id))
		else:
			Dialog().ok("Debug "+__version__,str(item),"NO IDS")

elif action == 'manualsearch':
	searchstring = getParam("searchstring", params)
	ManualSearch(searchstring)
	endOfDirectory(int(sys.argv[1]))

elif action == 'download':
	id = getParam("id", params)
	subs = download(id)
	for sub in subs:
		listitem = ListItem(label=sub)
		addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem,isFolder=False)
	endOfDirectory(int(sys.argv[1]))
elif action=='clean':
	try:
		rmtree(__temp__)
	except: pass