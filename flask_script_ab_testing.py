import os
import sys
import traceback

import random

import dill as pickle
import pandas as pd
import numpy as np
from scipy.stats import norm
from sklearn.externals import joblib
from sklearn.metrics.pairwise import cosine_similarity

from flask import Flask, render_template, request

sys.path.append(os.getcwd())


app = Flask(__name__)



# Make global variables
global imported_data, articleid


# this app.route controls where the following(?) function gets hosted (so XXX.XXX.X.X:XXXX/ for this case)
@app.route('/', methods = ['POST','GET'])
def generate_page():
	'''
	Generate the page where the model results are shown
	'''

	# pull some of the arguments 
	if request.method == "GET":
		articleid = request.args.get('articleid')

	if request.method == "POST":
		articleid = request.form['articleid']
		left = request.form['left']
		right = request.form['right']
		if left == '1':
			if keep_track.state == 0:
				record_input.increase_1()
			else:
				record_input.increase_2()
		if right == '1':
			if keep_track.state == 1:
				record_input.increase_1()
			else:
				record_input.increase_2()
		print(keep_track.state)
		print(articleid, left, right)

	# run the model (if error, just refresh with random page)
	try:
		string_output = rng_output(articleid)
	except:
		articleid = '0'
		string_output = rng_output(articleid)

	# the new rendered html page is returned 
	return render_template('generate_page_abtesting.html', variable=string_output)

@app.route('/summary')
def summary_page():
	'''
	Load the summary page
	'''
	string_output = record_input.output()

	return render_template('ab_test_summary.html', variable=string_output)

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
	
	rand_state = keep_track.random_pos()
	string_output = get_str(string_output, t5thr3, t5pr3, rand_state[model1name])
	string_output = get_str(string_output, t5thr4, t5pr4, rand_state[model2name])
	
	return string_output


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


class measurements:
	def __init__(self, model1name, model2name):
		self.model1name = model1name
		self.model2name = model2name
		self.model1_chosen = 0
		self.model2_chosen = 0
		self.list_chosen = []

	def increase_1(self):
		self.model1_chosen += 1
		self.list_chosen.append(1)

	def increase_2(self):
		self.model2_chosen += 1
		self.list_chosen.append(2)

	def output(self):
		output = dict()
		tot_count = self.model1_chosen + self.model2_chosen
		if tot_count != 0:
			prop1 = self.model1_chosen / float(tot_count)
			prop_compare = 0.5 # base case is 50/50 selected
			if prop1 > prop_compare:
				z = (prop1 - prop_compare) / np.sqrt(prop_compare*(1-prop_compare) / tot_count)
			else:
				z = (prop_compare - prop1) / np.sqrt(prop_compare*(1-prop_compare) / tot_count)
			
			pval = norm.sf(abs(z))
			if pval < 0.05:
				if prop1 < prop_compare:
					message = self.model1name + ' is selected (statistically significantly) less than ' + self.model2name + ' with 95% confidence.'
				else:
					message = self.model1name + ' is selected (statistically significantly) more than ' + self.model2name + ' with 95% confidence.'
			else:
				message = 'There is no statistical significance in the number of times each model was selected.'
			## outputs ##
			output['N'] = 'N=' + str(tot_count)
			output['zscore'] = 'Z=' + str(z)
			output['pval'] = 'p=' + str(pval)
			output['t_test_message'] = message
			output['model1count'] = self.model1_chosen
			output['model2count'] = self.model2_chosen
			
		else:
			output['N'] = tot_count
			output['zscore'] = 'NULL'
			output['pval'] = 'NULL'
			output['t_test_message'] = 'No counts recorded yet'
			output['model1count'] = self.model1_chosen
			output['model2count'] = self.model2_chosen
		return output

class keep_track:
	def __init__(self, model1name, model2name):
		self.model1name = model1name
		self.model2name = model2name

	def random_pos(self):
		self.state = random.randint(0,1)
		if self.state == 0:
			return {self.model1name:'1', self.model2name:'2'}
		else:
			return {self.model1name:'2', self.model2name:'1'}
			

if __name__ == '__main__':

	# If models are located in ~/ref_tables/. Otherwise, define other paths for cleaner directories
	ref_loc = os.getcwd() + '/ref_tables'

	# import the (global) variable(s) here
	imported_data = load_Data()

	# define random article for initializing
	articleid = '0'

	model1name = 'Model 3'; model2name = 'Model 4'
	record_input = measurements(model1name, model2name)
	keep_track = keep_track(model1name, model2name)


	app.run(debug=False, port=8996, host='0.0.0.0') # 0.0.0.0 makes it so you can use local ip address