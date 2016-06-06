import os
import urllib2
# from urllib.request import urlopen
import concurrent.futures
import time
import copy_reg
import types

def _pickle_method(m):
    if m.im_self is None:
        return getattr, (m.im_class, m.im_func.func_name)
    else:
        return getattr, (m.im_self, m.im_func.func_name)

copy_reg.pickle(types.MethodType, _pickle_method)

class URLTarget(object):
	def __init__(self, url, destination, timeout, url_tries):
		self.url = url
		self.destination = destination
		self.url_tries = url_tries
		self.url_tried = 0
		self.timeout = timeout
		self.success = False
		self.error = None

class DownloadManager(object):

	def download(self, url_target):

		while url_target.url_tried < url_target.url_tries:
			success = self._url2file(url_target)
			if not success and url_target.url_tried < url_target.url_tries:
				time.sleep(3)
			elif not success and url_target.url_tried == url_target.url_tries:
				self.report['failure'].append(url)
				return False
			elif success:
				self.report['success'].append(url)
				return True

	def _url2file(self, url_target):

		url_target.url_tried = url_target.url_tried + 1		
		try:
			if os.path.exists(url_target.destination): # already been downloaded?
				return True				
			remote_file = urllib2.urlopen(url_target.url, timeout=url_target.timeout)
			# remote_file = urlopen(url_target.url, timeout=url_target.timeout)
			package = remote_file.read()
			remote_file.close()			
			if not os.path.exists(os.path.dirname(url_target.destination)):
				os.makedirs(os.path.dirname(url_target.destination))			
			dest_file = open(url_target.destination, 'wb')
			dest_file.write(package)
			dest_file.close()			
			return True			
		except Exception as e:
			url_target.error = e
			return False			
		return True
	
	def __init__(self, num_cpu=5):

		self.report = {'success':[],'failure':[]}
		self.num_cpu = num_cpu
		self.target_urls = []
	
	def submit(self, urls, save_dir='.', prefix='', url_tries=3, timeout=10):

		if not os.path.exists(save_dir):
			raise ValueError('Destination folder does not exist.')

		for url in urls:
			try:
				media_url = url['MediaUrl']
				photo_id = url['ID']
				filetype = url['ContentType'].split('/')[-1]
				self.target_urls.append(URLTarget(
					media_url, 
					os.path.join(save_dir, prefix + '_' + photo_id + '.' + filetype), 
					timeout,
					url_tries
				))
			except KeyError:
				print('Key MediaUrl or ID not found')	
	def run(self):
		
		with concurrent.futures.ProcessPoolExecutor(max_workers=self.num_cpu) as executor:
			executor.map(self.download, self.target_urls)