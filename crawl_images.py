import os 
import sys
from photo_crawlers import * 

# load query list 
#queries_file = 'your querylist'
#DST_DIR = 'your destination directory'

def download_image_collection(download_site, queries_file, DST_DIR, key_id, start_ix, stop_ix):
	queries = {}
	with open(queries_file, 'rt') as fin:
		for line in fin: 
			entries = line.strip().split('\t')
			if len(entries) == 3:
				synset, keyword, query = entries
			else:
				keyword, query = entries
			queries[keyword] = query.split(',')
	
	if download_site == 'Flickr':
		thief = FlickrImage(int(key_id))
		num_imgs_per_query = 1500
	elif download_site == 'Bing':
		thief = BingImage(int(key_id))
		num_imgs_per_query = 1000
	
	count = -1
	for group, query in queries.iteritems():
		count += 1
		if count < start_ix:
			continue
		if count >= stop_ix:
			break	
		print 'Querying ', query
		dirname = os.path.join(DST_DIR, group)
		num_required_imgs = num_imgs_per_query
		if not os.path.isdir(dirname):
			os.mkdir(dirname)
			offset = 0
			start_page = 1;
		else:
			imglist = os.listdir(dirname)
			if len(imglist) >= num_imgs_per_query - 50:
				print '{} images exist, more than enough. Pass.'.format(len(imglist))
				continue
			else:
				offset = len(imglist)
				start_page = (offset + 50) / 500 + 1
				num_required_imgs -= offset
	
		# now start the engine!
		if download_site == 'Bing':
			for q in query:
				thief.crawl_photos(q, dirname, num_imgs_per_query, offset, verbose=True)
		elif download_site == 'Flickr':
			for q in query:
				thief.crawl_photos(q, dirname, num_required_imgs, start_page=start_page, verbose=True)
	
