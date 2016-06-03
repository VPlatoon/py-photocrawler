import os
import io
import time
import struct
import sys
import shutil
import urllib
import urllib2
import httplib
import json as simplejson
import numpy as np 
import flickr
import time
from threaded_download import ThreadedDownload
import logging
from datetime import datetime

class FlickrImage(object):
	# PUT YOUR API-KEYS HERE!!!
	keys = []

	def __init__(self, key_id):
		# print 'Possible keys to use:'
		# print '\n'.join(self.__class__.keys)
		flickr.API_KEY= self.__class__.keys[key_id]
		self.logger = logging.getLogger()
		self.logger.setLevel(logging.DEBUG)
		formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
		fh = logging.FileHandler('flickr_' + str(key_id) + '.log')
		fh.setLevel(logging.DEBUG)
		fh.setFormatter(formatter)
		self.logger.addHandler(fh)

	def retrieve_urls(self, query, number, page):
		# print datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ': retrieving photo ojbects with query ', query, '...'
		try:
			photos = flickr.photos_search(text=query, per_page=number, page=page, sort='relevance')
		except IOError:
			self.logger.error('IOError with query "{0}" at page {1}'.format(query, page))
			return []
		urls = []
		for photo in photos:
			try:
				urls.append(photo.getURL(size='Medium', urlType='source'))
			except:
				self.logger.error('Query {}: could not get url'.format(query))				
		return urls


	def download_images(self, urls, dir_photos, query, nimgs, page, verbose=False, filetype='jpg'):
		if verbose:
			widgets = ['{0}, page {1}: '.format(query, page), Percentage(), ' ', Bar(marker='.', left='[', right=']')]
			pbar = ProgressBar(widgets=widgets, maxval=len(urls)).start()
		
		rel = nimgs * (page - 1)
		count = 0
		for url in urls: 
				count += 1
				try:
					f = urllib2.urlopen(url, timeout=10)
				except IOError as  err:
					print(err)
					self.logger.error('IOError: {}'.format(url))
					continue
				except UnicodeError as err:
					self.logger.error('UnicodeError: {}'.format(url))
					continue
				except ValueError:
					self.logger.error('Something wrong with the header {}'.format(url))
					continue
				except urllib2.URLError:
					self.logger.error('URLError: {}'.format(url))
					continue
				except httplib.BadStatusLine:
					self.logger.error('BadStatusLine: {}'.format(url))
					continue
				except:
					self.logger.error('Unknown error {}'.format(url))
					continue
				
				try:
					name = url.split('/')[-1]
					fname = 'flickr_{0:0004d}_{1}'.format(rel+1, name)
					with open(os.path.join(dir_photos, fname.encode('utf8', 'ignore') + '.' + filetype), 'wb') as fout_img:
							fout_img.write(f.read())
				except:
					self.logger.error('Writing to disk error. Ignore {}'.format(fname))
					continue
				if verbose:
					pbar.update(count)
				rel += 1

		if verbose:
			pbar.finish()

	def crawl_photos(self, query, save_dir, number, start_page=1, verbose=False):

		page = start_page
		num_downloaded = 0
		while number > num_downloaded:
			self.logger.info('Download {0} images of query "{}" at page {2}'.format(500, query, page))
			urls = self.retrieve_urls(query, 500, page)
			if len(urls) == 0:
				self.logger.warning('Could not retrieve any url of query "{}"'.format(query))
				self.logger.warning('Could not retrieve any url.Stop here.')
				break
			self.download_images(urls, save_dir, query, 500, page, verbose)
			page += 1
			num_downloaded += 500

class GoogleImage(object):
	MAX_QUERIES_PER_DAY = 300
	num_queries = 0

	def __init__(self):
		history_fname = '~/.google_query.log'
		if not os.path.isfile(history_fname):
			with open(history_fname, 'wt') as fout:
				fout.write(self.__class__.MAX_QUERIES_PER_DAY)
			self.__class__.num_queries = self.__class__.MAX_QUERIES_PER_DAY
		else:
			with open(history_fname, 'rt') as fin:
				self.__class__.num_queries = int(fout.readline().strip())
				if self.__class__.num_queries == 0:
					t = os.path.getmtime(history_fname)
					date = datetime.datetime.fromtimestamp(t)
					today = datetime.datetime.today()

					if date.year != today.year or date.month != today.month or date.day != today.day:
						self.__class__.num_queries = self.__class__.MAX_QUERIES_PER_DAY
					else:
						raise Error('out of quota. Wait next till next day!')

	def __del__(self):
		history_fname = '/home/phong/.google_query.log'
		with open(history_fname, 'wt') as fout:
			fout.write(num_queries)

	def crawl_photos(self, query, save_dir, number, trace=True):
		query = query.replace(' ', '%20')

		dir_photos = os.path.join(save_dir, query)
		if not os.path.isdir(dir_photos):
			os.mkdir(dir_photos) 

		offset = 0
		while offset < number and num_queries > 0:
			try:
				url = ('https://ajax.googleapis.com/ajax/services/search/images?' + 'v=1.0&q=' + query + '&start='+str(offset)+'&userip=MyIP')
				request = urllib2.Request(url, None, {'Referer': 'testing'})
				response = urllib2.urlopen(request)
			except Error as err:
				print('I guess the quota is over... Check the error message for sure.')
				print(err)
				return

			# get result
			results = simplejson.load(response)
			dataInfo = results['responseData']['results']

			offset += len(dataInfo)
			self.__class__.num_queries -= 1
			
			if trace:
				fout = open(os.path.join(dir_photos, '.urls.txt'), 'at')

			for item in dataInfo:
				url = item['unescapedUrl']
				fname = item['imageId']
				f, mime = urllib.urlretrieve(url)
				shutil.copy(f, os.path.join(dir_photos, fname + '.JPEG'))
				fout.write('%s %s\n' % (fname, url))
			fout.close()

class BingImage(object):
	MAX_QUERIES_PER_MONTH = 5000
	num_queries = 0
	predefined_keys = ['lYZ2qYeIamdvVhxoBMtZQuvP5xXWKTVIDpJcffnkhLM', 'M+6gXLbHYptgvtoTNbMmFTtZ1NtbSu6ZJlf5ShMgTUc', 'MoP2UIaPYzaTzQ8wKR+HaLn79FNxn+eRyg0diL8goYI', 'kJAPULYaDDru0kkkFxEtarFVmJgfUlfbuskO1lBXpII', 'nMrSydrewQUaMwP8ejSpDgABeGN27c2sSolI7aokTZ0'] # PUT YOUR API-KEYS HERE!!!
	key = ''
	def __init__(self, key_id=0):
		self.__class__.key = self.__class__.predefined_keys[key_id]
		print 'key', self.__class__.key, ' is allocated.'
		self.logger = logging.getLogger()
		self.logger.setLevel(logging.DEBUG)
		formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
		fh = logging.FileHandler('bing_' + str(key_id) + '.log')
		fh.setLevel(logging.DEBUG)
		fh.setFormatter(formatter)
		self.logger.addHandler(fh)

	def crawl_photos(self, query, save_dir, number, offset=0, verbose=False):
		query = urllib.quote(query.encode('utf8'))
		# create credential for authentication
		user_agent = 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; FDM; .NET CLR 2.0.50727; InfoPath.2; .NET CLR 1.1.4322)'
		credentials = (':%s' % self.__class__.key).encode('base64')[:-1]

		# check that save_json_file exist
		save_json_file = os.path.join(save_dir, 'results.json')
		if os.path.isfile(save_json_file):
			# if so, load the existing items
			with open(save_json_file, 'rt') as fin:
				items = simplejson.load(fin)
			self.logger.info('Loading existing JSON data, get ' + str(len(items)) + ' records.')
			offset = len(items)
		else:
			items = []
		auth = 'Basic %s' % credentials
		if verbose:
			widgets = ['query: {0}'.format(query), Percentage(), ' ', Bar(marker='.', left='[', right=']')]
			if offset > number:
					offset = number

		while offset < number:
			#url = 'https://api.datamarket.azure.com/Data.ashx/Bing/Search/Image?Query=%27'+query+'%27&Image.Count=50&Image.Offset='+str(offset)+'&Image.Filters=Size:Large&Image.Filters=Size:Medium'+'$format=json'
			#url = 'https://api.datamarket.azure.com/Data.ashx/Bing/Search/Image?Query=%27'+query+'%27&$skip='+str(offset)+'&ImageFilters=%27Size%3ALarge%27&$format=json'
			url = 'https://api.datamarket.azure.com/Data.ashx/Bing/Search/Image?Query=%27'+query+'%27&$skip='+str(offset)+'&$format=json'

			try:
				request = urllib2.Request(url)
				request.add_header('Authorization', auth)
				request.add_header('User-Agent', user_agent)
				request_opener = urllib2.build_opener()
				response = request_opener.open(request) 
			except:
				self.logger.error('I guess the quota is over.')
				self.logger.error(e)
				# write down items in JSON format
				if len(items) > 0:
					self.write_json(save_json_file, items)
				# exit()
				return -1

			response_data = response.read()
			json_result = simplejson.loads(response_data)
			result_list = json_result['d']['results']
			self.logger.info('Get ' + str(len(result_list)) + ' of "' + query + '" at offset ' + str(offset))

			offset += len(result_list)
			# self.__class__.num_queries -= 1

			if len(result_list) == 0:
				self.logger.info('Not allowed downloading >1000 images. Stop here.')
				if len(items) > 0:
					self.write_json(save_json_file, items)
				return 0

			items += result_list
			if offset > number:
				offset = number
			
			# pause a little bit, this is not a DDOS attack
			time.sleep(3)

		self.write_json(save_json_file, items)
		return 1
		# self.download_photos(save_json_file, save_dir)

	def write_json(self, save_json_file, items):
		# write down items in JSON format
		with io.open(save_json_file, 'wt', encoding='utf8') as fout:
			data = simplejson.dumps(items, indent=4, sort_keys=True, ensure_ascii=False, encoding='utf8')
			fout.write(data)
		self.logger.info('Saved photo records.')


	def download_photos(self, save_json_file, save_dir, num_thread=4):

		if not os.path.isfile(save_json_file):
			self.logger.error('JSON file ' + save_json_file + ' not found.')
			raise ValueError('JSON file ' + save_json_file + ' not found.')
		with open(save_json_file, 'rt') as fin:
			items = simplejson.load(fin)
		if len(items) == 0:
			self.logger.warning('The file content is empty. Are you sure photo metadata was downloaded?')
			return
		downloader = ThreadedDownload(items, destination=save_dir, thread_count=num_thread, prefix='bing')
		downloader.run()
		self.logger.info('Downloaded %(success)s of %(total)s' % {'success': len(downloader.report['success']), 'total': len(items)})
			

class TooSlowException(Exception):
    pass

def convertBToMb(bytes):
    """converts Bytes to Megabytes"""
    bytes = float(bytes)
    megabytes = bytes / 1048576
    return megabytes

def dlProgress(count, blockSize, totalSize):
    global startTime

    # alreadyLoaded = count*blockSize
    # timePassed = time.time() - startTime
    # transferRate = convertBToMb(alreadyLoaded) / timePassed # mbytes per second
    # transferRate *= 60 # mbytes per minute

    # if transferRate < 10 and timePassed > 2:
    #     raise TooSlowException
    time_passed = time.time() - startTime
    if time_passed > 5:
    	raise TooSlowException


startTime = time.time()
