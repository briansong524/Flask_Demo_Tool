import os
import sys
import traceback

import random

import dill as pickle
import pandas as pd
import numpy as np
from sklearn.externals import joblib
from sklearn.metrics.pairwise import cosine_similarity

from flask import Flask, render_template, request

sys.path.append(os.getcwd())#os.path.abspath('/home/bsong/'))


app = Flask(__name__)


# If models are located in ~/ref_tables/. Otherwise, define other paths for cleaner directories
ref_loc = os.getcwd() + '/ref_tables'


def load_Data():
	'''
	Load necessary files here (csvs, pkls, models, etc.).
	These (generaly global) variables will be loaded upon running this script 
	'''

	print('Importing Data')

	# can store into dictionary to make things cleaner
	imported_data = dict()

	imported_data['model_3_mat'] = joblib.load(ref_loc + '/model_specific_cos_mat.pkl')
	imported_data['model_4_mat'] = joblib.load(ref_loc + '/model_diverse_cos_mat.pkl')

	with open(ref_loc + '/model_specific.pkl','rb') as pickle_in:
		imported_data['model_3'] = pickle.load(pickle_in)

	with open(ref_loc + '/model_diverse.pkl','rb') as pickle_in:
		imported_data['model_4'] = pickle.load(pickle_in)

	with open(ref_loc + '/corpus_index.pkl', 'rb') as pickle_load:
		imported_data['corpus_index'] = pickle.load(pickle_load)

	with open(ref_loc + '/article_data.pkl','rb') as pickle_in:
		imported_data['article_data'] = pickle.load(pickle_in)
	
	print('Done')

	return imported_data

# Make imported variable(s) global
global imported_data

# import the (global) variable(s) here
imported_data = load_Data()


# this app.route controls where the following(?) function gets hosted (so XXX.XXX.X.X:XXXX/ for this case)
@app.route('/', methods = ['GET'])
def generate_page():
	'''
	Generate the page where the model results are shown
	'''

	# pull some of the arguments 
	articleid = request.args.get('articleid')

	# run the model 
	try:
		string_output = rng_output(articleid)
	except:
		articleid = '0'
		string_output = rng_output(articleid)
	
	# the new rendered html page is returned 
	return render_template('generate_page.html', variable=string_output)


def rng_output(articleid):
	'''
	function to return a dictionary of {'variable_str':'variable_value_as_str'} which is how the html page
	(easily) reads the values to display.

	This section is pretty messy and can be much better written
	'''

	def remove_nonascii(unclean_text):
		try:
			cleaned_text = ''.join(''.join([i if ord(i) < 128 else '' for i in text]) for text in unclean_text)
			return cleaned_text
		except:
			return unclean_text


	def process_text(value):
		if type(value) == unicode:
			document = nlp(value)
		else:
			document = nlp(unicode(value))
		processed_document = u''

		for token in document:
			if token.lemma_[0] != "'":
				if token.pos_ != 'PROPN':
					if token.is_stop == False:
						if token.is_punct == False:
							processed_document = processed_document + token.lemma_ + u' '
		return processed_document[:-1]

	def get_str(string_output, top_5_thread, top_5_prob, suffix_):
		for j in range(5):
			try:
				thread_ind = top_5_thread[j]
				string_output['sequoia_id_' + str(j) + '_' + suffix_] = 'Sequoia ID #' + str(thread_ind)
				string_output['simil_' + str(j) + '_' + suffix_] = 'Similarity: ' + str(round(top_5_prob[j],4))
				#string_output['simil_' + str(j) + '_' + suffix_] = 'word count: ' + str(top_5_prob)

				string_output['title_' + str(j) + '_' + suffix_] = remove_nonascii(imported_data['article_data'][imported_data['article_data'].sequoia_id == thread_ind]['title'])
				string_output['text_' + str(j) + '_' + suffix_] = remove_nonascii(imported_data['article_data'][imported_data['article_data'].sequoia_id == thread_ind]['meta_description'])
				string_output['link_' + str(j) + '_' + suffix_] = 'https://www.lawyers.com/legal-info/' + imported_data['article_data'][imported_data['article_data'].sequoia_id == thread_ind]['url'].iloc[0].split('/legal-info/')[1]
			except Exception as e:
				type_, value_, traceback_ = sys.exc_info()
				tb = traceback.format_exception(type_, value_, traceback_)
				print('\n' + ' '.join(tb))
				print('exception occured %s',str(e))
				string_output['sequoia_id_' + str(j) + '_' + suffix_] = 'Null'
				string_output['simil_' + str(j) + '_' + suffix_] = 'Null'
				string_output['title_' + str(j) + '_' + suffix_] = 'Null'
				string_output['text_' + str(j) + '_' + suffix_] = 'Null'
		return string_output


	## Begin rng_output() here ##

	# designed to randomly select a row number if default index value is returned. 
	# otherwise, the id the user defined will be used 
	if ((articleid == '0') | (articleid == '')):
		rand_ind = random.sample(range(imported_data['model_3_mat'].shape[0]), 1)[0]
		articleid = rand_ind
	else:
		rev_corpus_index = {j:i for i,j in imported_data['corpus_index'].items()}
		articleid = rev_corpus_index[int(articleid)]



	string_output = dict()

	string_output['line'] = '---------------------------------------------------------------------------------------'

	
	test_thread_id = articleid
	string_output['article_title'] = remove_nonascii(imported_data['article_data'][imported_data['article_data'].sequoia_id == int(imported_data['corpus_index'][test_thread_id])]['title']) 
	string_output['thread_id'] = 'Sequoia ID #' + str(int(imported_data['corpus_index'][test_thread_id]))
	string_output['test_string'] = remove_nonascii(imported_data['article_data'][imported_data['article_data'].sequoia_id == int(imported_data['corpus_index'][test_thread_id])]['meta_description'])
	string_output['test_link'] = 'https://www.lawyers.com/legal-info/' + imported_data['article_data'][imported_data['article_data'].sequoia_id == int(imported_data['corpus_index'][test_thread_id])]['url'].iloc[0].split('/legal-info/')[1]

	## calculate similarity

	sim_scores_m3 = cosine_similarity(imported_data['model_3_mat'][test_thread_id,:], imported_data['model_3_mat'])[0] #list in list
	sim_scores_m4 = cosine_similarity(imported_data['model_4_mat'][test_thread_id,:], imported_data['model_4_mat'])[0]

	sorted_enum_m3 = sorted(enumerate(sim_scores_m3), key=lambda x:x[1], reverse = True)
	sorted_enum_m4 = sorted(enumerate(sim_scores_m4), key=lambda x:x[1], reverse = True)

	t5thr3 = [imported_data['corpus_index'][i[0]] for i in sorted_enum_m3[1:6]]
	t5thr4 = [imported_data['corpus_index'][i[0]] for i in sorted_enum_m4[1:6]]

	t5pr3 = [i[1] for i in sorted_enum_m3[1:6]]
	t5pr4 = [i[1] for i in sorted_enum_m4[1:6]]
	
	string_output = get_str(string_output, t5thr3, t5pr3, '1')
	string_output = get_str(string_output, t5thr4, t5pr4, '2')
	
	return string_output






if __name__ == '__main__':
	app.run(debug=False, port=8997, host='0.0.0.0')
