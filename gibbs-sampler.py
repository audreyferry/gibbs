#!/usr/bin/env python3
# LoopNumberAtWhichWeStartTracking = 20		# Will need this later in development

import sys
import os
import random
import math
import json
import jsonpickle
import time
import datetime
import copy
#import numpy     # TODAY ONLY
g_encoding = "asci"  # "utf8"


# PARAMETERS   # probably want shorter segments initially (so BREAKPROB higher than 0.1)
BitsPerLetter = 5
BREAKPROB     = 0.3		#0.3		# 0.5  #0.4 #0.3  #0.2    # 0.1   # where does this probability come from? is it a statistic about languages in general/English?
DEFAULTCOUNT  = 1		# 0.5  # Used in divide_charges_among_instances() and in get_plog()
PLOGCOEFF     = 3 		# 3		# used in get_plog_charge()
bgPLOGCOEFF     = 3  #3  #1 		# 3		# used in get_bg_plog_charge()
PENALTYFACTOR = 1.5		# extra factor in get_plog_charge() for "new" segment (not in dictionary)	1.0	 1.5  2.0  1.25  1.3
REBASE_PERIOD = 10		# number of iterations between calls to rebase()   # standard setting = 10
FLOAT_INF = float("inf")


NumberOfIterations = 1          # 160	 # 200	 # 400	
ResumeLoopno = 0									# Note - may want to (set a flag and) give a file to load, then get the ResumeLoop from the file 
print("\nNumber of iterations =", NumberOfIterations)
if ResumeLoopno > 0:
	print("Resume processing starting at loopno =", ResumeLoopno)

SaveState = False		# True


## ---------------------------------------------------------------------------------------##
class Segment:   # think   <morpheme> for morphology,  <word-type> or dictionary entry for wordbreaking
## ---------------------------------------------------------------------------------------##
	def __init__(self, segment_text):
		self.segment_text          = segment_text
		self.count                 = 0 
		self.phonocost             = len(segment_text) * float(BitsPerLetter)
		self.ordercost             = math.log (math.factorial(len(segment_text)), 2)
		#<self.ordercost           = 0.0>		# <produces interesting results>
		self.inclusioncost         = 1.0
		self.phonocost_portion     = 0.0		# phonocost / count
		self.ordercost_portion     = 0.0		# etc.
		self.inclusioncost_portion = 0.0
		self.sum_dictcosts_portion = 0.0 		# (phonocost + ordercost + inclusioncost) / count

		self.plog                  = 0.0		# CAUTION: plog depends on total_pieces_count.
												# self.plog is not updated except when this segment is involved in a parsing decision.
												# Use self.get_plog(totalsegmentcount) for correct value.
												# SEE ALSO document.fetch_plogged_segment_from_dictionary
												
												
												
	def divide_charges_among_instances(self):  #CHANGE THIS WHEN SWITCH OVER TO PROJECTED COUNTS 
		if self.count != 0:
			divisor = self.count
		else:
			divisor = DEFAULTCOUNT
		self.phonocost_portion     = self.phonocost/divisor		# Note that phonocost is float; also '/' is true division in python3
		self.ordercost_portion     = self.ordercost/divisor
		self.inclusioncost_portion = self.inclusioncost/divisor
		self.sum_dictcosts_portion = self.phonocost_portion + self.ordercost_portion + self.inclusioncost_portion


	def get_plog(self, totalsegmentcount):  #CHANGE THIS WHEN SWITCH OVER TO PROJECTED COUNTS
		if self.count >= 1:
			return math.log( (totalsegmentcount / float(self.count)), 2 )
		else:
			return math.log( (totalsegmentcount / float(DEFAULTCOUNT)), 2 )

				
#	def get_plog_charge(self, totalsegmentcount):
#		return PLOGCOEFF * self.get_plog(totalsegmentcount)
	def get_plog_charge(self, totalsegmentcount):
		if self.count != 0:
			return PLOGCOEFF * self.get_plog(totalsegmentcount)
		else:
			return PENALTYFACTOR * PLOGCOEFF * self.get_plog(totalsegmentcount)
		
	def get_instance_cost(self, totalsegmentcount):   # RENAME AS get_instance_ug_cost
		return self.get_plog_charge(totalsegmentcount) + self.sum_dictcosts_portion
		

#	def get_bg_plog(self, backbigramcount):
#		return -math.log(( self.bigram_count[(backsegment.segment_text, self.segment_text)] / float(backsegment.count) ), 2)

#	def get_bg_plog_charge(self, backbigramcount):
#		return bgPLOGCOEFF * self.get_bg_plog(backbigramcount)

#	def get_bg_instance_cost(self, backbigramount):
#		return self.get_bg_plog_charge(backbigramcount) + self.sum_dictcosts_portion
		

## ---------------------------------------------------------------------------------------##
class Bigram:
## ---------------------------------------------------------------------------------------##
	def __init__(self, segobject0, segobject1, bigram_count):
		self.seg0		= segobject0
		self.seg1		= segobject1
		self.count      = bigram_count 


	def get_conditioned_plog(self):
		assert(self.seg0.count >= 1)
		return -math.log( self.count/self.seg0.count, 2 )
		
	def get_conditioned_plog_charge(self):
		return bgPLOGCOEFF * self.get_conditioned_plog()		# Currently bgPLOGCOEFF = 1, PENALTYFACTOR not used
		
	def get_conditioned_instance_cost(self):
		print(self.seg0.segment_text, self.seg1.segment_text, " \t", self.seg0.count, " \t", self.count, " \t%6.2f" % self.get_conditioned_plog_charge(), file=outfile_biplogs)  	
		
		return self.get_conditioned_plog_charge() + self.seg1.sum_dictcosts_portion
												
												
## ---------------------------------------------------------------------------------------##
class Line:     # a bounded expression  <word in dx1 file>    <line in corpus>
## ---------------------------------------------------------------------------------------##
	def __init__(self, unbroken_text):
		self.unbroken_text              = unbroken_text	# (former self.word)
		self.breaks                     = []
		self.pieces                     = []		# list of strings  <morphs>   <words>   NOT segment objects 

		self.piecesorder_cost			= 0.0
		self.total_cost 		        = 0.0		# Since only local information is needed for parsing decisions,
														# total_cost for the line and the lists below are not maintained at intermediate stages.
														# Use the document function compute_brokenline_cost() (former EvaluateWordParse)
														# to obtain line cost information.
														# Use the document function populate_line_displaylists() to fill the lists below 
														# in order to display cost details by segment and cost component.

		self.count_list					= []		# List of segment counts, in proper order.
		self.phonocost_portion_list 	= []		# List per segment of phonocost_portion, in proper order. Similarly for other list variables.
		self.ordercost_portion_list     = []		# The lists are used to arrange segment information attractively for display.
		self.inclusioncost_portion_list = []		# Are they useful to retain? Should they be in a separate Display class?
		self.plog_list 		            = []
		self.subtotal_list              = []		# list per segment of following quantity: 
													# ordercost_portion + phonocost_portion + inclusioncost_portion + plog
		
		self.true_text					= []
		self.true_breaks				= []
				

	def getpiece(self, pieceno):
		return self.unbroken_text[self.breaks[pieceno-1]:self.breaks[pieceno]]		# note that getpiece(k) returns pieces[k-1]
																					# for example, getpiece(1) returns pieces[0]
																					
	# EXAMPLE FOR NEXT TWO FUNCTIONS  
	# line.unbroken_text = abcdefghij
	# line.breaks = [0, 2, 5, 7, 10]
	# line.pieces = [ab, cde, fg, hij]

	def populate_pieces_from_breaks(self):
		#self.pieces = []
		#for n in range(len(self.breaks)-1):
		#	self.pieces.append(self.unbroken_text[self.breaks[n]:self.breaks[n+1]])
		self.pieces = []
		start = 0
		for brk in self.breaks[1:]:
			self.pieces.append(self.unbroken_text[start:brk])
			start = brk
		
	def populate_breaks_from_pieces(self):
		self.breaks = [0]
		for piece in self.pieces:
			self.breaks.append(self.breaks[-1] + len(piece))
			
			
	def displaytextonly(self, outfile):
		print(self.unbroken_text, file=outfile)
		print("     breaks:",  self.breaks, file=outfile)
		print("     pieces:", end=' ', file=outfile)				# FIX SPACING?	 
		#for n in range(1,len(self.breaks)):
		#	print(self.getpiece(n), "", end=' ', file=outfile)
		for piece in self.pieces:
			print(piece,  "", end=' ', file=outfile)
		print(file=outfile)


	def display_detail(self, outfile):
		FormatString1 = "%20s"
		FormatString2 = "%8.1f"
		FormatString3 = "%8s"
		FormatString4 = "%8d"

		print("\n", self.unbroken_text, file=outfile)
		print("breaks:",  self.breaks, file=outfile)		
		print(FormatString1 %("pieces:"), end=' ', file=outfile)   # FIX SPACING?		 
		#for n in range(1,len(self.breaks)):
		#	print(FormatString3 %(self.getpiece(n)), end=' ', file=outfile)
		for piece in self.pieces:
			print(FormatString3 % piece, end=' ', file=outfile)
		print(file=outfile)

		print(FormatString1 %("count:"), end=' ', file=outfile)	
		for item in self.count_list:
			print(FormatString4 %(item), end=' ', file=outfile)
		print(file=outfile)
		print(FormatString1 %("plog:"), end=' ', file=outfile)	
		for item in self.plog_list:
			print(FormatString2 %(item), end=' ', file=outfile)
		print(file=outfile)
		print(FormatString1 %("log |piece|!:"), end=' ', file=outfile)	
		for item in self.ordercost_portion_list:
			print(FormatString2 %(item), end=' ', file=outfile)
		print(file=outfile)
		print(FormatString1 %("phono info:"), end=' ', file=outfile)	
		for item in self.phonocost_portion_list:
			print(FormatString2 %(item), end=' ', file=outfile)
		print(file=outfile)
		print(FormatString1 %("inclusion list cost:"), end=' ', file=outfile)	
		for item in self.inclusioncost_portion_list:
			print(FormatString2 %(item), end=' ', file=outfile)
		print(file=outfile)

		print(FormatString1 %("subtotal:"), end=' ', file=outfile)	
		for item in self.subtotal_list:
			print(FormatString2 %(item), end=' ', file=outfile)
			#Total += item   # self.total_cost is computed in EvaluateWordParse (including also logfacword)
		print(file=outfile)

		logfacword = self.piecesorder_cost
		print(FormatString1 %("log (num_pieces!):"), end=' ', file=outfile)
		print(FormatString2 %( logfacword ), end=' ', file=outfile)
		print(file=outfile)
		print(FormatString1 %("Total:"), end=' ', file=outfile)
		print(FormatString2 %( self.total_cost  ), file=outfile)


	def displaytoscreen_textonly(self):
		print(self.unbroken_text)
		print("     breaks:",  self.breaks)
		print("     pieces:", end=' ')				# FIX SPACING?	 
		#for n in range(1,len(self.breaks)):
		#	print(self.getpiece(n), "", end=' ', file=outfile)
		for piece in self.pieces:
			print(piece,  "", end=' ')
		print()


	def displaytoscreen_detail(self):
		FormatString1 = "%20s"
		FormatString2 = "%8.1f"
		FormatString3 = "%8s"		 
		FormatString4 = "%8d"		 

		print(self.unbroken_text)
		print("breaks", self.breaks)		

		print(FormatString1 %("pieces:"), end=' ')		 
		#for n in range(1,len(self.breaks)):
		#	print(FormatString3 %(self.getpiece(n)), end=' ')
		for piece in self.pieces:
			print(FormatString3 % piece, end=' ')
		print() 

		print(FormatString1 %("count:"), end=' ')	
		for item in self.count_list:
			print(FormatString4 %(item), end=' ')
		print()
		print(FormatString1 %("plog:"), end=' ')	
		for item in self.plog_list:
			print(FormatString2 %(item), end=' ')
		print() 
		print(FormatString1 %("log |piece|!:"), end=' ')	
		for item in self.ordercost_portion_list:
			print(FormatString2 %(item), end=' ')
		print() 
		print(FormatString1 %("phono info:"), end=' ')	
		for item in self.phonocost_portion_list:
			print(FormatString2 %(item), end=' ')
		print() 

		print(FormatString1 %("inclusion list cost:"), end=' ')	
		for item in self.inclusioncost_portion_list:
			print(FormatString2 %(item), end=' ')
		print() 
		print(FormatString1 %("subtotal:"), end=' ')	
		for item in self.subtotal_list:
			print(FormatString2 %(item), end=' ')
			#Total += item
		print() 

		logfacword = self.piecesorder_cost
		print(FormatString1 %("log (num_pieces!):"), end=' ')
		print(FormatString2 %( logfacword ), end=' ')
		print() 
		print(FormatString1 %("Total:"), end=' ')
		print(FormatString2 %( self.total_cost  ))
		 
 
 
	def break_cover(self, point):	
		# for the first breakpoint that is greater than or equal to the point, return the breakpoint and its index
		if point not in range(1, len(self.unbroken_text)):
			print("Error in break_cover(): point (=", point, ") must satisfy 0 < point < ", len(self.unbroken_text), "for line = '", self.unbroken_text, "'.")
			sys.exit()
		for n in range(1, len(self.breaks)):     # Note self.breaks[0] = 0.  
			if point <= self.breaks[n]:
				return (self.breaks[n], n)
		return (-1, -1)   #should never happen!          


 
## ---------------------------------------------------------------------------------------##
class Document:	 #  <dx1 file>    <corpus>
## ---------------------------------------------------------------------------------------##
	def __init__(self):   # this_item ???
		self.line_object_list     		= []			# list of Line objects   (former WordObjectList)
		self.segment_object_dictionary	= {}			# dictionary  key: piece					value: segment object
		self.bigram_count_dictionary	= {}			# dictionary  key: 2-tuple of text pieces	value: count
		self.lineboundary_segment		= Segment('#')
		self.totalsegmentcount   		= 0
		self.merge_count         		= 0
		self.split_count          		= 0
		self.merge_newsegment_count		= 0				# these 3 added on Feb. 2, 2016
		self.split_1newsegment_count	= 0
		self.split_2newsegments_count	= 0
		self.split_merge_history 		= []
		self.break_precision			= 0.0			# these 6 added on Feb. 21, 2016
		self.break_recall				= 0.0
		self.token_precision			= 0.0
		self.token_recall				= 0.0
		self.dictionary_precision		= 0.0
		self.dictionary_recall			= 0.0
		self.addedandtrue_devcount		= 0.0			# these 4 are for diagnosing DR (DictionaryRecall); added on Feb. 25, 2016
		self.deletedandtrue_devcount	= 0.0
		self.addedandtrue_dictionary	= {}			# key is piece; value is the count in the true_segment_dictionaryx
		self.deletedandtrue_dictionary	= {}
		self.overall_cost				= 0.0
		self.other_statistics     		= 0.0			# What should be measured?
		self.random_state				= None			# save state of random number generator in this spot
														# so that it will be preserved by pickling
		self.true_segment_dictionary	= {}
		self.true_totalsegmentcount		= 0
		
		

	def output_corpuslines_detail(self, outfile, loopno):
		print("----------------------------------------\nLoop number:", loopno, file=outfile)
		print("----------------------------------------", file=outfile)
		for line in self.line_object_list:
			self.populate_line_displaylists(line)
			line.display_detail(outfile)			# displays text followed by line cost, detailed by segment and component

	def output_corpuslines_textonly(self, outfile, loopno):
		print("----------------------------------------\nLoop number:", loopno, file=outfile)
		print("----------------------------------------", file=outfile)
		for line in self.line_object_list:
			line.displaytextonly(outfile)			# displays only unbroken line and its parse
			print("       cost: %7.3f\n" % line.total_cost, end=' ', file=outfile)	
	
	def output_gibbspieces(self, outfile, loopno):
		print("----------------------------------------\nLoop number:", loopno, file=outfile)
		print("----------------------------------------", file=outfile)

		# Additional information is stored in the segment_object_dictionary,
		# but only count will be displayed on the outfile.
		
		
		reduced_dictionary = {}
		for this_piece, this_segment in self.segment_object_dictionary.items():
			reduced_dictionary[this_piece] = this_segment.count
		#countslist = sorted(reduced_dictionary.items(), key = lambda x:(x[1],x[0]), reverse=True)	#primary sort key is count, secondary is alphabetical
		countslist = sorted(reduced_dictionary.items(), key = lambda x:x[0])						#secondary sort is alphabetical (ascending)
		countslist = sorted(countslist, key = lambda x:x[1], reverse=True)							#primary sort is by count (descending)

		print("\ntotalsegmentcount =", self.totalsegmentcount, file=outfile)	
		print("\n=== Dictionary ===", file=outfile)
#		for n in range(len(countslist)):
#			print(n, countslist[n][0], countslist[n][1], file=outfile)
		for n in range(len(countslist)):
			print("%6d" % n, "\t%5d" % countslist[n][1], "\t", countslist[n][0], file=outfile)
		
	def output_bigrams(self, outfile, loopno):
		print("----------------------------------------\nLoop number:", loopno, file=outfile)
		print("----------------------------------------", file=outfile)
		countslist = sorted(self.bigram_count_dictionary.items(), key = lambda x:x[0])				#secondary sort is alphabetical (ascending)
		countslist = sorted(countslist, key = lambda x:x[1], reverse=True)							#primary sort is by count (descending)
		for n in range(len(countslist)):
			print("%6d" % n, "\t%5d" % countslist[n][1], "\t", countslist[n][0], file=outfile)
	

	def output_addedandtrue(self, outfile, loopno):
		print("----------------------------------------\nLoop number:", loopno, file=outfile)
		print("----------------------------------------", file=outfile)
		#countslist = sorted(reduced_dictionary.items(), key = lambda x:(x[1],x[0]), reverse=True)	#primary sort key is count, secondary is alphabetical
		countslist = sorted(self.addedandtrue_dictionary.items(), key = lambda x:x[0])				#secondary sort is alphabetical (ascending)
		countslist = sorted(countslist, key = lambda x:x[1], reverse=True)							#primary sort is by count (descending)

		print("\n=== addedandtrue_dictionary ===", file=outfile)
		for n in range(len(countslist)):
			print("%6d" % n, "\t%5d" % countslist[n][1], "\t", countslist[n][0], file=outfile)
		
	def output_deletedandtrue(self, outfile, loopno):
		print("----------------------------------------\nLoop number:", loopno, file=outfile)
		print("----------------------------------------", file=outfile)
		#countslist = sorted(reduced_dictionary.items(), key = lambda x:(x[1],x[0]), reverse=True)	#primary sort key is count, secondary is alphabetical
		countslist = sorted(self.deletedandtrue_dictionary.items(), key = lambda x:x[0])			#secondary sort is alphabetical (ascending)
		countslist = sorted(countslist, key = lambda x:x[1], reverse=True)							#primary sort is by count (descending)

		print("\n=== deletedandtrue_dictionary ===", file=outfile)
		for n in range(len(countslist)):
			print("%6d" % n, "\t%5d" % countslist[n][1], "\t", countslist[n][0], file=outfile)
		
	
	def fetch_plogged_segment_from_dictionary(self, piece):    # BETTER: return  (this_segment, plog)
		this_segment = self.segment_object_dictionary[piece]
		if this_segment.count == 0:
			print("Error in fetch_plogged_segment_from_dictionary for piece ='", piece, "': if segment is in the dictionary, its count should not be 0")
			sys.exit()		
		this_segment.plog = math.log( self.totalsegmentcount / float(this_segment.count), 2 )
		return this_segment

		
	def new_segment_object(self, piece, count):
		this_segment = Segment(piece)
		this_segment.count = count
		this_segment.divide_charges_among_instances()						# replaces 0 by DEFAULTCOUNT
		this_segment.plog = this_segment.get_plog(self.totalsegmentcount)	# replaces 0 by DEFAULTCOUNT
		return this_segment

		
	def build_dictionaries_from_pieces(self):		# N.B. last piece in each line is '#'
		self.segment_object_dictionary = {}
		self.bigram_count_dictionary = {}
		self.totalsegmentcount = 0

#		# line_boundary is needed for bigrams
#		# #The plan for now is that it should have no cost, and should not add to totalsegmentcount.
#		self.lineboundary_ = Segment("#")									# does not contribute to totalsegmentcount
		self.lineboundary_segment.count = len(self.line_object_list)
#		self.segment_object_dictionary["#"] = line_boundary
		
		for ln in self.line_object_list:
			for piece in ln.pieces:
				self.totalsegmentcount += 1								# ALERT - for any item in or about to go into the dictionary,
				if not piece in self.segment_object_dictionary:			# increment totalsegmentcount BEFORE populating its plog variable		  
					self.segment_object_dictionary[piece] = self.new_segment_object(piece, 1)
				else:
					self.segment_object_dictionary[piece].count += 1
		
#			if ln.unbroken_text[0:12]  =="youtakeoutof":
#				print("line pieces:", ln.pieces)

			backpiece = "#"
			for piece in ln.pieces:
				textpair = (backpiece, piece)	  #tuple
				if not textpair in self.bigram_count_dictionary:
					self.bigram_count_dictionary[textpair] = 1
				else:
					self.bigram_count_dictionary[textpair] += 1

#				if ln.unbroken_text[0:12]  =="youtakeoutof":
#					print("textpair =", textpair, "   count =", self.bigram_count_dictionary[textpair])
				backpiece = piece



#			IS THIS NEEDED? probably not  YES IT IS NEEDED
			textpair = (ln.pieces[-1], "#")
			if not textpair in self.bigram_count_dictionary:
				self.bigram_count_dictionary[textpair] = 1
			else:
				self.bigram_count_dictionary[textpair] += 1			
#			if ln.unbroken_text[0:12]  =="youtakeoutof":
#				print("textpair =", textpair, "   count =", self.bigram_count_dictionary[textpair])

		
#		self.totalsegmentcount -= len(self.line_object_list)	# "#" must be present in each line to form bigrams, but should not go into precision computation
		
		# fill in the information that depends on the count	 
		for sgmt in self.segment_object_dictionary.values():
			sgmt.divide_charges_among_instances()
			sgmt.get_plog(self.totalsegmentcount)   # POSSIBLY REMOVE   2016_03_31
			

		


	def initial_segmentation(self):
#		dictionary = self.segment_object_dictionary
		for ln in self.line_object_list:
			start = 0		 
			ln.breaks.append(0)								# always put a break at the beginning
			for n in range(1, len(ln.unbroken_text)):		# won't randomly put a break at the beginning or end
				if random.random() < BREAKPROB:				# about every 10 (= 1/BREAKPROB) letters add a break
					piece = ln.unbroken_text[start:n]
					ln.pieces.append(piece)
					ln.breaks.append( n )
					start = n	
#					self.totalsegmentcount += 1				# ALERT - for any item in or about to go into the dictionary,
#					if not piece in dictionary:				# increment totalsegmentcount BEFORE populating its plog variable		  
#						dictionary[piece] = self.new_segment_object(piece, 1)
#					else:
#						dictionary[piece].count += 1
					
			if start < len(ln.unbroken_text):      # should always be true...
				piece = ln.unbroken_text[start:]
				ln.pieces.append(piece)
				ln.breaks.append( len(ln.unbroken_text) )   # always put a break at the end
#				self.totalsegmentcount += 1
#				if not piece in dictionary:
#					dictionary[piece] = self.new_segment_object(piece, 1)
#				else:
#					dictionary[piece].count += 1
#			ln.pieces.append("#")

#		# Now that forming of segments is complete, 
#		# fill in the information that depends on their count.	 
#		for sgmt in self.segment_object_dictionary.values():
#			sgmt.divide_charges_among_instances()
#			sgmt.get_plog(self.totalsegmentcount)

		self.build_dictionaries_from_pieces()			# REPLACES 	


	def compare_alt_parse(self, line):
		# EXPLANATORY NOTE
		###		point = 1 + int(random.random() * (len(line.unbroken_text)-1)) 
		# Before python3, this line and the first line of code below were equivalent.
		# randrange changed in python3, so now program output doesn't match pre-python3 runs.
		# Using random.random() as shown above DOES exactly reproduce pre-python3 results,
		# except for spacing and ordering.
		
		# In this function, we package configuration data uniformly for all cases, including edge cases,
		# to simplify treatment in subsequent processing functions. 

		# The "alt" dictionaries here hold temporary values, for calculating the cost of the alternative parse; 
		## the "curr" dictionaries are more of an organizing convenience.
		curr_segment_info = {}		# entries here will agree with the corresponding entries in the Document object dictionaries
		curr_bigram_info  = {}
		alt_segment_info  = {}		# entries here will be modified from the corresponding entries in the Document object dictionaries
		alt_bigram_info   = {}		# except for spacing and ordering.

	
		attentionpoint = random.randrange( 1, len(line.unbroken_text))	# selects a possible spot for a change, not before all text or after.
																		# attentionpoint k refers to a current or potential break between text points k-1 and k.
																		# Suppose len(line.unbroken_text) = 5
																		# Text index runs from 0 through 4. Don't pick 0. Don't pick 5.
																		# But OK to pick 4. That splits off the last character of the line.
		coverbrkpt, coverbrkindex = line.break_cover(attentionpoint)

		# SPLITTING:
		if attentionpoint < coverbrkpt:										# attentionpoint may be any character within its piece except the first
		
			leftbreak  = line.breaks[coverbrkindex-1]
			rightbreak = line.breaks[coverbrkindex]       					# Note rightbreak == coverbrkpt

			# Consider a modification of current parse at the selected location

			# current configuration
			singlepiece = line.unbroken_text[leftbreak:rightbreak]			# Note singlepiece == line.pieces[coverbrkindex-1]
			assert(singlepiece in self.segment_object_dictionary)
			#if singlepiece not in self.segment_object_dictionary:
				#print("Error in CompareAltParse: singlepiece (=", singlepiece, ") not found in dictionary at line ='", line.unbroken_text, "'.")
				#sys.exit()
			#single_segment = self.fetch_plogged_segment_from_dictionary(singlepiece)
			curr_segment_info[singlepiece] = self.segment_object_dictionary[singlepiece]

			#if line.unbroken_text[0:15] == "mostlymeatandpo":
				#print("SPLIT")
				#print("line.pieces: ", line.pieces)
				#print("attnpoint =", attentionpoint, "   leftbreak =", leftbreak, "   rightbreak =", rightbreak, "   singlepiece =", singlepiece)
			#if singlepiece == line.pieces[0]:
			if leftbreak == 0:			# equiv, if coverbrkindex-1 == 0
				precedingpiece = '#'
				#preceding_segment = self.lineboundary_segment
				curr_segment_info[precedingpiece] = self.lineboundary_segment
			else:
				precedingpiece    = line.pieces[coverbrkindex-2]
				#if line.unbroken_text[0:15] == "mostlymeatandpo":
					#print("precedingpiece =", precedingpiece)
				assert(precedingpiece in self.segment_object_dictionary)		# there should be no "new" pieces
				#preceding_segment = self.fetch_plogged_segment_from_dictionary(precedingpiece)
				curr_segment_info[precedingpiece] = self.segment_object_dictionary[precedingpiece]
			
			#if singlepiece == line.pieces[-1]:
			if rightbreak == len(line.unbroken_text):		# equiv., if rightbreak == line.breaks[-1] or coverbrkindex == -1
				followingpiece = '#'
				#following_segment = self.lineboundary_segment
				curr_segment_info[followingpiece] = self.lineboundary_segment
			else:
				followingpiece   = line.pieces[coverbrkindex]
				assert(followingpiece in self.segment_object_dictionary)		# there should be no "new" pieces
				#following_segment = self.fetch_plogged_segment_from_dictionary(followingpiece)
				curr_segment_info[followingpiece] = self.segment_object_dictionary[followingpiece]
				
			curr_bigram_info[(precedingpiece, singlepiece)] = self.bigram_count_dictionary[(precedingpiece, singlepiece)]
			curr_bigram_info[(singlepiece, followingpiece)] = self.bigram_count_dictionary[(singlepiece, followingpiece)]
					

			# alternate configuration 	
			
			leftpiece  = line.unbroken_text[leftbreak:attentionpoint]
			rightpiece = line.unbroken_text[attentionpoint:rightbreak]
			
			if leftpiece in self.segment_object_dictionary:
				leftseg = copy.deepcopy(self.segment_object_dictionary[leftpiece])
				leftseg.count += 1
				leftseg.divide_charges_among_instances()
				alt_segment_info[leftpiece] = leftseg
			else:
				alt_segment_info[leftpiece]  = self.new_segment_object(leftpiece, 1)
			
			if rightpiece in alt_segment_info:		# i.e., rightpiece == leftpiece
				alt_segment_info[rightpiece].count += 1
			elif rightpiece in self.segment_object_dictionary:
				rightseg = copy.deepcopy(self.segment_object_dictionary[rightpiece])
				rightseg.count += 1
				rightseg.divide_charges_among_instances()
				alt_segment_info[rightpiece] = rightseg
			else:
				alt_segment_info[rightpiece]  = self.new_segment_object(rightpiece, 1)


#			if leftpiece == rightpiece:
#				samepiece = leftpiece
#				if samepiece in self.segment_object_dictionary:
#					sameseg = copy.deepcopy(self.segment_object_dictionary[samepiece])
#					sameseg.count += 2
#					sameseg.divide_charges_among_instances()
#					alt_segment_info[samepiece] = sameseg
#				else:
#					alt_segment_info[samepiece]  = self.new_segment_object(samepiece, 2)			
				
			
			if (precedingpiece, leftpiece) in self.bigram_count_dictionary:
				alt_bigram_info[(precedingpiece, leftpiece)] = 1 + self.bigram_count_dictionary[(precedingpiece, leftpiece)]
			else:
				alt_bigram_info[(precedingpiece, leftpiece)] = 1		

			if (leftpiece, rightpiece) in self.bigram_count_dictionary:
				alt_bigram_info[(leftpiece, rightpiece)] = 1 + self.bigram_count_dictionary[(leftpiece, rightpiece)]
			else:
				alt_bigram_info[(leftpiece, rightpiece)] = 1		

			if (rightpiece, followingpiece) in self.bigram_count_dictionary:
				alt_bigram_info[(rightpiece, followingpiece)] = 1 + self.bigram_count_dictionary[(rightpiece, followingpiece)]
			else:
				alt_bigram_info[(rightpiece, followingpiece)] = 1		



			
			
			# In the standard case we consider singlepiece vs. (leftpiece and rightpiece).
			# When possible, we consider in addition whether to merge a separated single character with the preceding or following segment, as appropriate.
			# For each case:
			#  - calculate alternative costs 
			#  - select among alternatives by sampling 
			#  - update information
		
			leftsingleton_case  = (len(leftpiece)  == 1) and (leftbreak  != 0)
			rightsingleton_case = (len(rightpiece) == 1) and (rightbreak != len(line.unbroken_text))
			
		
			#if (not leftsingleton_case and not rightsingleton_case):
			if True:
				#decision = self.compare_bg_simple_split(line, single_segment, projected_left_segment, projected_right_segment, preceding_segment, following_segment)
				decision = self.compare_bg_simple_split(line, singlepiece, leftpiece, rightpiece, precedingpiece, followingpiece, curr_segment_info, curr_bigram_info, alt_segment_info, alt_bigram_info)
				if decision == 'alt':
					#self.update_for_bg_simple_split(line, attentionpoint, coverbrkindex, single_segment, projected_left_segment, projected_right_segment, preceding_segment, following_segment)
					self.update_for_bg_simple_split(line, attentionpoint, coverbrkindex, singlepiece, leftpiece, rightpiece, precedingpiece, followingpiece, curr_segment_info, curr_bigram_info, alt_segment_info, alt_bigram_info)
				# NOTE: if decision == 'current', make no changes


			#else:		# special treatment for single characters
			elif False:		# special treatment for single characters
				if leftsingleton_case:
					precedingpiece   = line.pieces[coverbrkindex-2]
					preceding_segment = self.fetch_plogged_segment_from_dictionary(precedingpiece)
				if rightsingleton_case:
					followingpiece   = line.pieces[coverbrkindex]
					following_segment = self.fetch_plogged_segment_from_dictionary(followingpiece)
			
				if (leftsingleton_case and not rightsingleton_case):
					leftmergedpiece = precedingpiece + leftpiece
					if leftmergedpiece in self.segment_object_dictionary:
						leftmerged_segment = self.fetch_plogged_segment_from_dictionary(leftmergedpiece)
					else:
						leftmerged_segment = self.new_segment_object(leftmergedpiece, 0)

					decision = self.compare_leftsingleton_split(line, single_segment, left_segment, right_segment, preceding_segment, leftmerged_segment)

					if decision == 'alt1':
						self.update_for_simple_split(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment)
					elif decision == 'alt2':
						self.update_for_leftsingleton_split(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment, preceding_segment, leftmerged_segment)
					# NOTE: if decision == 'current', make no changes


				elif (rightsingleton_case and not leftsingleton_case):
					rightmergedpiece = rightpiece + followingpiece
					if rightmergedpiece in self.segment_object_dictionary:
						rightmerged_segment = self.fetch_plogged_segment_from_dictionary(rightmergedpiece)
					else:
						rightmerged_segment = self.new_segment_object(rightmergedpiece, 0)

					decision = self.compare_rightsingleton_split(line, single_segment, left_segment, right_segment, following_segment, rightmerged_segment)

					if decision == 'alt1':
						self.update_for_simple_split(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment)
					elif decision == 'alt2':
						self.update_for_rightsingleton_split(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment, following_segment, rightmerged_segment)
					# NOTE: if decision == 'current', make no changes


				elif (rightsingleton_case and leftsingleton_case):		# This case should really be "else:"
					leftmergedpiece = precedingpiece + leftpiece
					if leftmergedpiece in self.segment_object_dictionary:
						leftmerged_segment = self.fetch_plogged_segment_from_dictionary(leftmergedpiece)
					else:
						leftmerged_segment = self.new_segment_object(leftmergedpiece, 0)
						
					rightmergedpiece = rightpiece + followingpiece
					if rightmergedpiece in self.segment_object_dictionary:
						rightmerged_segment = self.fetch_plogged_segment_from_dictionary(rightmergedpiece)
					else:
						rightmerged_segment = self.new_segment_object(rightmergedpiece, 0)
						

					decision = self.compare_bothsingletons_split(line, single_segment, left_segment, right_segment, preceding_segment, following_segment, leftmerged_segment, rightmerged_segment)

					if decision == 'alt1':
						self.update_for_simple_split(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment)
					elif decision == 'alt2':
						self.update_for_leftsingleton_split(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment, preceding_segment, leftmerged_segment)
					elif decision == 'alt3':
						self.update_for_rightsingleton_split(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment, following_segment, rightmerged_segment)
					elif decision == 'alt4':
						self.update_for_bothsingletons_split(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment, preceding_segment, following_segment, leftmerged_segment, rightmerged_segment)
					# NOTE: if decision == 'current', make no changes

				else:   # used when developing and testing individual parts of preceding code; should not be reached in regular operation.
					decision = self.compare_simple_split(line, single_segment, left_segment, right_segment)
					if decision == 'alt':
						self.update_for_simple_split(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment)
		
		
		# MERGING:
		elif attentionpoint == line.breaks[coverbrkindex]:						# here attentionpoint is the first character within its piece

			leftbreak  = line.breaks[coverbrkindex-1]
			rightbreak = line.breaks[coverbrkindex+1]

			# Consider a modification of current parse at the selected location

			# current configuration
			leftpiece  = line.unbroken_text[leftbreak:attentionpoint]		# leftpiece  == line.pieces[coverbrkindex-1]
			rightpiece = line.unbroken_text[attentionpoint:rightbreak]		# rightpiece == line.pieces[coverbrkindex]
			
			#if leftpiece not in self.segment_object_dictionary:
				#print("Error in CompareAltParse: leftpiece (= ", leftpiece, ") not found in dictionary at line = '", line.unbroken_text, "'.")
				#sys.exit()
			#if rightpiece not in self.segment_object_dictionary:
				#print("Error in CompareAltParse: rightpiece (= ", rightpiece, ") not found in dictionary at line = '", line.unbroken_text, "'.")
				#sys.exit()
			assert(leftpiece in self.segment_object_dictionary)
			assert(rightpiece in self.segment_object_dictionary)
			#left_segment  = self.fetch_plogged_segment_from_dictionary(leftpiece)
			#right_segment = self.fetch_plogged_segment_from_dictionary(rightpiece)	
			curr_segment_info[leftpiece]  = self.segment_object_dictionary[leftpiece]
			curr_segment_info[rightpiece] = self.segment_object_dictionary[rightpiece]

			#if leftpiece == line.pieces[0]:
			if leftbreak == 0:
				precedingpiece = '#'
				#preceding_segment = self.lineboundary_segment
				curr_segment_info[precedingpiece] = self.lineboundary_segment
			else:
				precedingpiece    = line.pieces[coverbrkindex-2]
				assert(precedingpiece in self.segment_object_dictionary)		# there should be no "new" pieces
				#preceding_segment = self.fetch_plogged_segment_from_dictionary(precedingpiece)
				curr_segment_info[precedingpiece] = self.segment_object_dictionary[precedingpiece]
			
			#if leftpiece == line.pieces[0]:
			if rightbreak == len(line.unbroken_text):
				followingpiece = '#'
				#following_segment = self.lineboundary_segment
				curr_segment_info[followingpiece] = self.lineboundary_segment
			else:
				followingpiece   = line.pieces[coverbrkindex+1]
				assert(followingpiece in self.segment_object_dictionary)		# there should be no "new" pieces
				#following_segment = self.fetch_plogged_segment_from_dictionary(followingpiece)
				curr_segment_info[followingpiece] = self.segment_object_dictionary[followingpiece]
			
			curr_bigram_info[(precedingpiece, leftpiece)]  = self.bigram_count_dictionary[(precedingpiece, leftpiece)]
			curr_bigram_info[(leftpiece, rightpiece)]      = self.bigram_count_dictionary[(leftpiece, rightpiece)]
			curr_bigram_info[(rightpiece, followingpiece)] = self.bigram_count_dictionary[(rightpiece, followingpiece)]

			# alternate configuration 	
			singlepiece = line.unbroken_text[leftbreak:rightbreak]
			if singlepiece in self.segment_object_dictionary:
				#single_segment = self.fetch_plogged_segment_from_dictionary(singlepiece)
				singleseg = copy.deepcopy(self.segment_object_dictionary[singlepiece])
				singleseg.count += 1
				singleseg.divide_charges_among_instances()
				alt_segment_info[singlepiece] = singleseg
			else:
				alt_segment_info[singlepiece] = self.new_segment_object(singlepiece, 1)


			if (precedingpiece, singlepiece) in self.bigram_count_dictionary:
				alt_bigram_info[(precedingpiece, singlepiece)] = 1 + self.bigram_count_dictionary[(precedingpiece, singlepiece)]
			else:
				alt_bigram_info[(precedingpiece, singlepiece)] = 1

			if (singlepiece, followingpiece) in self.bigram_count_dictionary:
				alt_bigram_info[(singlepiece, followingpiece)] = 1 + self.bigram_count_dictionary[(singlepiece, followingpiece)]
			else:
				alt_bigram_info[(singlepiece, followingpiece)] = 1


			#if line.unbroken_text[0:15] == "mostlymeatandpo":
				#print("MERGE")
				#print("line.pieces: ", line.pieces)
				#print("leftpiece =", leftpiece, "   rightpiece =", rightpiece, "   singlepiece =", singlepiece, "   precedingpiece =", precedingpiece, "Followingpiece=", followingpiece)
						

			# In the standard case we consider (leftpiece and rightpiece) vs.singlepiece (that is, the merger of leftpiece and rightpiece). 
			# If either (or both) of the original pieces is a single character, we consider as an additional alternative whether to merge the single-character segment instead with the preceding or following segment, as appropriate.
			# For each case:
			#  - calculate alternative costs 
			#  - select among alternatives by sampling 
			#  - update information

			leftsingleton_case  = (len(leftpiece)  == 1) and (leftbreak  != 0)
			rightsingleton_case = (len(rightpiece) == 1) and (rightbreak != len(line.unbroken_text))
			
		
			#if (not leftsingleton_case and not rightsingleton_case):
			if True:
				#decision = self.compare_bg_simple_merge(line, projected_single_segment, left_segment, right_segment, preceding_segment, following_segment)
				decision = self.compare_bg_simple_merge(line, singlepiece, leftpiece, rightpiece, precedingpiece, followingpiece, curr_segment_info, curr_bigram_info, alt_segment_info, alt_bigram_info)
				if decision == 'alt':
					#self.update_for_bg_simple_merge(line, attentionpoint, coverbrkindex, projected_single_segment, left_segment, right_segment, preceding_segment, following_segment)
					self.update_for_bg_simple_merge(line, attentionpoint, coverbrkindex, singlepiece, leftpiece, rightpiece, precedingpiece, followingpiece, curr_segment_info, curr_bigram_info, alt_segment_info, alt_bigram_info)
				# NOTE: if decision == 'current', make no changes


			#else:		# special treatment for single characters
			elif False:
				if leftsingleton_case:
					precedingpiece   = line.pieces[coverbrkindex-2]
					preceding_segment = self.fetch_plogged_segment_from_dictionary(precedingpiece)
				if rightsingleton_case:
					followingpiece   = line.pieces[coverbrkindex+1]
					following_segment = self.fetch_plogged_segment_from_dictionary(followingpiece)
			
				if (leftsingleton_case and not rightsingleton_case):
					leftmergedpiece = precedingpiece + leftpiece
					if leftmergedpiece in self.segment_object_dictionary:
						leftmerged_segment = self.fetch_plogged_segment_from_dictionary(leftmergedpiece)
					else:
						leftmerged_segment = self.new_segment_object(leftmergedpiece, 0)

					decision = self.compare_leftsingleton_merge(line, single_segment, left_segment, right_segment, preceding_segment, leftmerged_segment)

					if decision == 'alt1':
						self.update_for_simple_merge(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment)
					elif decision == 'alt2':
						self.update_for_leftsingleton_merge(line, attentionpoint, coverbrkindex, left_segment, preceding_segment, leftmerged_segment)
					# NOTE: if decision == 'current', make no changes


				elif (rightsingleton_case and not leftsingleton_case):
					rightmergedpiece = rightpiece + followingpiece
					if rightmergedpiece in self.segment_object_dictionary:
						rightmerged_segment = self.fetch_plogged_segment_from_dictionary(rightmergedpiece)
					else:
						rightmerged_segment = self.new_segment_object(rightmergedpiece, 0)

					decision = self.compare_rightsingleton_merge(line, single_segment, left_segment, right_segment, following_segment, rightmerged_segment)

					if decision == 'alt1':
						self.update_for_simple_merge(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment)
					elif decision == 'alt2':
						self.update_for_rightsingleton_merge(line, attentionpoint, coverbrkindex, right_segment, following_segment, rightmerged_segment)
					# NOTE: if decision == 'current', make no changes


				elif (rightsingleton_case and leftsingleton_case):		# This case should really be "else:"
					leftmergedpiece = precedingpiece + leftpiece
					if leftmergedpiece in self.segment_object_dictionary:
						leftmerged_segment = self.fetch_plogged_segment_from_dictionary(leftmergedpiece)
					else:
						leftmerged_segment = self.new_segment_object(leftmergedpiece, 0)
						
					rightmergedpiece = rightpiece + followingpiece
					if rightmergedpiece in self.segment_object_dictionary:
						rightmerged_segment = self.fetch_plogged_segment_from_dictionary(rightmergedpiece)
					else:
						rightmerged_segment = self.new_segment_object(rightmergedpiece, 0)
						

					decision = self.compare_bothsingletons_merge(line, single_segment, left_segment, right_segment, preceding_segment, following_segment, leftmerged_segment, rightmerged_segment)

					if decision == 'alt1':
						self.update_for_simple_merge(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment)
					elif decision == 'alt2':
						self.update_for_leftsingleton_merge(line, attentionpoint, coverbrkindex, left_segment, preceding_segment, leftmerged_segment)
					elif decision == 'alt3':
						self.update_for_rightsingleton_merge(line, attentionpoint, coverbrkindex, right_segment, following_segment, rightmerged_segment)
					elif decision == 'alt4':
						self.update_for_bothsingletons_merge(line, attentionpoint, coverbrkindex, left_segment, right_segment, preceding_segment, following_segment, leftmerged_segment, rightmerged_segment)
					# NOTE: if decision == 'current', make no changes

				else:   # used when developing and testing individual parts of preceding code; should not be reached in regular operation.
					decision = self.compare_simple_merge(line, single_segment, left_segment, right_segment)
					if decision == 'alt':
						self.update_for_simple_merge(line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment)


				
	# N.B. Except for the adjustments to line's piecesorder_cost [log(factorial( len(self.pieces) ))],
	# these 'compare_' functions could be made to work for both Splitting and Merging operations.
	# Rename the alternatives with descriptive names; then the calling function could distinguish
	# which is the current and which the alternate configurations. 

	# SPLITTING	#	
	# ----------------------------------------------------------------------------- #
	# FUNCTIONS FOR SAMPLING AMONG LOCAL CONFIGURATIONS WEIGHTED ACCORDING TO COST. #
	# THESE FUNCTIONS APPLY TO DIFFERENT CASES. ALL BEGIN WITH THE WORD 'compare_'. #
	# ----------------------------------------------------------------------------- #
	# def compare_bg_simple_split(self, line, single_segment, projected_left_segment, projected_right_segment, preceding_segment, following_segment):
	def compare_bg_simple_split(self, line, singlepiece, leftpiece, rightpiece, precedingpiece, followingpiece, curr_segment_info, curr_bigram_info, alt_segment_info, alt_bigram_info):
		preceding_segment = curr_segment_info[precedingpiece]
		following_segment = curr_segment_info[followingpiece]
		single_segment = curr_segment_info[singlepiece]
		left_segment   = alt_segment_info[leftpiece]				#if leftpiece == rightpiece, then left_segment and right_segment are the same object
		right_segment  = alt_segment_info[rightpiece]

		#singlepiece = single_segment.segment_text
		#leftpiece   = projected_left_segment.segment_text
		#rightpiece  = projected_right_segment.segment_text
		#precedingpiece = preceding_segment.segment_text
		#followingpiece = following_segment.segment_text


		#outfile_items = open("itemfile", mode='w') 
		##print("Are there any entries in bigram_count_dictionary? len(dictionary) =", len(self.bigram_count_dictionary))
		#for k,v in self.bigram_count_dictionary.items():
		#	print(k, "\t", v, file = outfile_items)
		#outfile_items.close()
		#k = tuple([precedingpiece, singlepiece])
		#count_list = [v for (k, v) in self.bigram_count_dictionary.items() if (k[0] == precedingpiece and k[1]==singlepiece)]
		#print("length of count_list:", len(count_list))
		#print("count =", count_list[0])

		#if line.unbroken_text[0:18]  == "thebondissuewillgo":
			#print("line pieces:", line.pieces)

		
		# local contribution to line cost as currently configured
		# print("prec:", precedingpiece, "   single:", singlepiece, "   following:", followingpiece)
		bigram_for_prec_single      = Bigram(preceding_segment, single_segment,  curr_bigram_info[(precedingpiece, singlepiece)])
		bigram_for_single_following = Bigram(single_segment, following_segment,  curr_bigram_info[(singlepiece, followingpiece)])				

		current_contribution = bigram_for_prec_single.get_conditioned_instance_cost()	+ \
							   bigram_for_single_following.get_conditioned_instance_cost()
								

		# alternate configuration

		#if (precedingpiece, leftpiece) in self.bigram_count_dictionary:
		#	projected_prec_left_count = 1 + self.bigram_count_dictionary[(precedingpiece, leftpiece)]
		#else:
		#	projected_prec_left_count = 1		
		#
		#if (leftpiece, rightpiece) in self.bigram_count_dictionary:
		#	projected_left_right_count = 1 + self.bigram_count_dictionary[(leftpiece, rightpiece)]
		#else:
		#	projected_left_right_count = 1		
		#
		#if (rightpiece, followingpiece) in self.bigram_count_dictionary:
		#	projected_right_following_count = 1 + self.bigram_count_dictionary[(rightpiece, followingpiece)]
		#else:
		#	projected_right_following_count = 1		

		bigram_for_prec_left  = Bigram(preceding_segment, left_segment, alt_bigram_info[(precedingpiece, leftpiece)])
		bigram_for_left_right = Bigram(left_segment, right_segment, alt_bigram_info[(leftpiece, rightpiece)])
		bigram_for_right_following = Bigram(right_segment, following_segment, alt_bigram_info[(rightpiece, followingpiece)])
		
		alt_contribution = bigram_for_prec_left.get_conditioned_instance_cost()			+ \
						   bigram_for_left_right.get_conditioned_instance_cost()		+ \
						   bigram_for_right_following.get_conditioned_instance_cost()	+ \
			               math.log(1 + len(line.pieces), 2)
		# last addend is adjustment to present value of log(factorial( len(self.pieces) ))
			
#		# FOR DETERMINISTIC SELECTION, USE THESE LINES 
#		#if alt_contribution < current_contribution:	
#			return 'alt'
#		else
#			return 'current'

		# FOR SAMPLING, USE THESE LINES		
		normalizing_factor = 1.0 / (current_contribution + alt_contribution)
		norm_compl_current = alt_contribution * normalizing_factor
		norm_compl_alt = current_contribution * normalizing_factor
		
		hypothesis_list = [('current', norm_compl_current),  ('alt', norm_compl_alt)]
		selection = weighted_choice(hypothesis_list)
		#print(selection)
		
		#if line.unbroken_text[0:18]  =="thebondissuewillgo":
			#print("compare_bg_simple_split  SELECTION:", selection)
		
		return selection

				
	# THIS FUNCTION SHOULD NOT BE USED BECAUSE IT HASN'T BEEN MODIFIED FOR BIGRAM MODEL
	def compare_leftsingleton_split(self, line, single_segment, left_segment, right_segment, preceding_segment, leftmerged_segment):  

		# local contribution to line cost as currently configured
		current_contribution = preceding_segment.get_instance_cost(self.totalsegmentcount) + \
							single_segment.get_instance_cost(self.totalsegmentcount)

		# alternate configuration
		alt1_contribution = preceding_segment.get_instance_cost(self.totalsegmentcount) + \
							left_segment.get_instance_cost(self.totalsegmentcount)		+ \
							right_segment.get_instance_cost(self.totalsegmentcount)		+ \
			                math.log(1 + len(line.pieces), 2)
		# last addend is adjustment to present value of log(factorial( len(self.pieces) ))
		
		# another alternate configuration
		alt2_contribution = leftmerged_segment.get_instance_cost(self.totalsegmentcount) + \
							right_segment.get_instance_cost(self.totalsegmentcount)


		method = 'sampling'

		# FOR DETERMINISTIC SELECTION, USE THESE LINES
		if method == 'determinate':
			min_contribution = min(current_contribution, alt1_contribution, alt2_contribution)	
			if min_contribution == alt1_contribution:
				return 'alt1'
			elif min_contribution == alt2_contribution:
				return 'alt2'
			else:
				return 'current'
			
		# FOR SAMPLING, USE THESE LINES
		elif method == 'sampling':
			normalizing_factor = 1.0 / (2 * (current_contribution + alt1_contribution + alt2_contribution))
			norm_compl_current = (alt1_contribution + alt2_contribution) * normalizing_factor
			norm_compl_alt1 = (current_contribution + alt2_contribution) * normalizing_factor
			norm_compl_alt2 = (current_contribution + alt1_contribution) * normalizing_factor 
		
			hypothesis_list = [('current',norm_compl_current),  ('alt1',norm_compl_alt1),  ('alt2',norm_compl_alt2)]
			selection = weighted_choice(hypothesis_list)
		
			#print()
			#print("cost_current =", current_contribution, "  cost_alt1 =", alt1_contribution, "  cost_alt2 =", alt2_contribution)
			#print("weight_current =", norm_compl_current, "  weight_alt1 =", norm_compl_alt1, "  weight_alt2 =", norm_compl_alt2)
			#print()
		
			return selection
		

	# THIS FUNCTION SHOULD NOT BE USED BECAUSE IT HASN'T BEEN MODIFIED FOR BIGRAM MODEL
	def compare_rightsingleton_split(self, line, single_segment, left_segment, right_segment, following_segment, rightmerged_segment):

		# local contribution to line cost as currently configured
		current_contribution =  single_segment.get_instance_cost(self.totalsegmentcount) + \
								following_segment.get_instance_cost(self.totalsegmentcount)

		# alternate configuration
		alt1_contribution = left_segment.get_instance_cost(self.totalsegmentcount)		+ \
							right_segment.get_instance_cost(self.totalsegmentcount)		+ \
							following_segment.get_instance_cost(self.totalsegmentcount) + \
							math.log(1 + len(line.pieces), 2)
							# last addend is adjustment to present value of log(factorial( len(self.pieces) ))
		
		# another alternate configuration
		alt2_contribution = left_segment.get_instance_cost(self.totalsegmentcount) + \
							rightmerged_segment.get_instance_cost(self.totalsegmentcount)


		method = 'sampling'
							
		# FOR DETERMINISTIC SELECTION, USE THESE LINES
		if method == 'determinate':
			min_contribution = min(current_contribution, alt1_contribution, alt2_contribution)	
			if min_contribution == alt1_contribution:
				return 'alt1'
			elif min_contribution == alt2_contribution:
				return 'alt2'
			else:
				return 'current'
			
		# FOR SAMPLING, USE THESE LINES
		elif method == 'sampling':
			normalizing_factor = 1.0 / (2 * (current_contribution + alt1_contribution + alt2_contribution))
			norm_compl_current = (alt1_contribution + alt2_contribution) * normalizing_factor
			norm_compl_alt1 = (current_contribution + alt2_contribution) * normalizing_factor
			norm_compl_alt2 = (current_contribution + alt1_contribution) * normalizing_factor 
		
			hypothesis_list = [('current',norm_compl_current),  ('alt1',norm_compl_alt1),  ('alt2',norm_compl_alt2)]
			selection = weighted_choice(hypothesis_list)
		
			#print()
			#print("cost_current =", current_contribution, "  cost_alt1 =", alt1_contribution, "  cost_alt2 =", alt2_contribution)
			#print("weight_current =", norm_compl_current, "  weight_alt1 =", norm_compl_alt1, "  weight_alt2 =", norm_compl_alt2)
			#print()
		
			return selection


	# THIS FUNCTION SHOULD NOT BE USED BECAUSE IT HASN'T BEEN MODIFIED FOR BIGRAM MODEL
	def compare_bothsingletons_split(self, line, single_segment, left_segment, right_segment, preceding_segment, following_segment, leftmerged_segment, rightmerged_segment):
	
		# local contribution to line cost as currently configured
		current_contribution = preceding_segment.get_instance_cost(self.totalsegmentcount)	+ \
							single_segment.get_instance_cost(self.totalsegmentcount)		+ \
							following_segment.get_instance_cost(self.totalsegmentcount)

		# four alternate configurations		
		alt1_contribution = preceding_segment.get_instance_cost(self.totalsegmentcount) 	+ \
							left_segment.get_instance_cost(self.totalsegmentcount)			+ \
							right_segment.get_instance_cost(self.totalsegmentcount)			+ \
							following_segment.get_instance_cost(self.totalsegmentcount)		+ \
			                math.log(1 + len(line.pieces), 2)
							# last addend is adjustment to the current value
							# of  log(factorial( len(self.pieces) ))
		
		alt2_contribution = leftmerged_segment.get_instance_cost(self.totalsegmentcount)	+ \
							right_segment.get_instance_cost(self.totalsegmentcount)			+ \
							following_segment.get_instance_cost(self.totalsegmentcount)

		alt3_contribution = preceding_segment.get_instance_cost(self.totalsegmentcount) 	+ \
							left_segment.get_instance_cost(self.totalsegmentcount)			+ \
							rightmerged_segment.get_instance_cost(self.totalsegmentcount)
		
		alt4_contribution = leftmerged_segment.get_instance_cost(self.totalsegmentcount)	+ \
							rightmerged_segment.get_instance_cost(self.totalsegmentcount)	- \
							math.log(len(line.pieces), 2)
							# last addend is adjustment to the current value
							# of  log(factorial( len(self.pieces) ))


		method = 'sampling'

#		# FOR DETERMINISTIC SELECTION, USE THESE LINES
		if method == 'determinate':
			min_contribution = min(current_contribution, alt1_contribution, alt2_contribution, alt3_contribution, alt4_contribution)	
			if min_contribution == alt1_contribution:
				return 'alt1'
			elif min_contribution == alt2_contribution:
				return 'alt2'
			elif min_contribution == alt3_contribution:
				return 'alt3'
			elif min_contribution == alt4_contribution:
				return 'alt4'
			else:
				return 'current'
			
		# FOR SAMPLING, USE THESE LINES
		elif method == 'sampling':
			sum = current_contribution + alt1_contribution + alt2_contribution + alt3_contribution + alt4_contribution
			normalizing_factor = 1.0 / (4 * sum)

			norm_compl_current = (sum - current_contribution) * normalizing_factor
			norm_compl_alt1 = (sum - alt1_contribution) * normalizing_factor
			norm_compl_alt2 = (sum - alt2_contribution) * normalizing_factor 
			norm_compl_alt3 = (sum - alt3_contribution) * normalizing_factor
			norm_compl_alt4 = (sum - alt4_contribution) * normalizing_factor 
		
			hypothesis_list = [ ('current',norm_compl_current),  
								('alt1',norm_compl_alt1),  
								('alt2',norm_compl_alt2),
								('alt3',norm_compl_alt3),  
								('alt4',norm_compl_alt4) ]

			selection = weighted_choice(hypothesis_list)
		
			return selection


	# SPLITTING	#	
	# ---------------------------------------------------------------------------- #
	# FUNCTIONS FOR UPDATING RECORDS ACCORDING TO SELECTED PARSING MODIFICATIONS.  #
	# THESE FUNCTIONS APPLY TO DIFFERENT CASES. ALL BEGIN WITH THE WORD 'update_'. #
	# ---------------------------------------------------------------------------- #
	# def update_for_bg_simple_split(self, line, attentionpoint, coverbrkindex, single_segment, projected_left_segment, projected_right_segment, preceding_segment, following_segment): 			
	def update_for_bg_simple_split(self, line, attentionpoint, coverbrkindex, singlepiece, leftpiece, rightpiece, precedingpiece, followingpiece, curr_segment_info, curr_bigram_info, alt_segment_info, alt_bigram_info): 			
		preceding_segment = curr_segment_info[precedingpiece]
		following_segment = curr_segment_info[followingpiece]
		single_segment = curr_segment_info[singlepiece]
		left_segment   = alt_segment_info[leftpiece]				#if leftpiece == rightpiece, then left_segment and right_segment are the same object
		right_segment  = alt_segment_info[rightpiece]

		#singlepiece = single_segment.segment_text
		#leftpiece   = projected_left_segment.segment_text
		#rightpiece  = projected_right_segment.segment_text
		#precedingpiece = preceding_segment.segment_text
		#followingpiece = following_segment.segment_text
		#
		#if line.unbroken_text[0:18]  =="thebondissuewillgo":
			#print("update_for_bg_simple_split")
			#print("singlepiece =", singlepiece)
			#print("leftpiece =", leftpiece)
			#print("rightpiece =", rightpiece)
			#print("precedingpiece =", precedingpiece)
			#print("followingpiece =", followingpiece)
			
		# UPDATE THE PARSE
		line.piecesorder_cost += math.log(1 + len(line.pieces), 2)
		line.pieces[coverbrkindex-1] = leftpiece				# i.e., replace singlepiece by leftpiece
		line.breaks.insert(coverbrkindex, attentionpoint)		# or use addcut  
		line.pieces.insert(coverbrkindex, rightpiece)
				 
		# UPDATE GLOBAL COUNTS
		self.totalsegmentcount += 1
		self.split_count += 1
		if (left_segment.count == 1 and right_segment.count == 1):	
			self.split_2newsegments_count += 1
		elif (left_segment.count == 1 or right_segment.count == 1):
			self.split_1newsegment_count += 1
		elif (leftpiece == rightpiece and left_segment.count == 2):
			self.split_1newsegment_count += 1
				
		# UPDATE DICTIONARY ENTRIES
		self.decrement_segment_record(single_segment)		# modifies the entry in the Document segment_object_dictionary
		self.increment_segment_record_bg(left_segment)		# replaces the entry in the Document segment_object_dictionary 
		self.increment_segment_record_bg(right_segment)		# replaces the entry in the Document segment_object_dictionary
		
		self.decrement_bigram_record((precedingpiece, singlepiece))
		self.decrement_bigram_record((singlepiece, followingpiece))
		self.increment_bigram_record((precedingpiece, leftpiece))
		self.increment_bigram_record((leftpiece, rightpiece))
		self.increment_bigram_record((rightpiece, followingpiece))
		
		#if '#' in self.segment_object_dictionary:
			#print("At end of build_dictionaries, '#' is in dictionary")
			#print("us:YES")
		#else:
			#print("At end of build_dictionaries, '#' is NOT in dictionary")
			#print("us:NO")
		


	def update_for_simple_split(self, line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment): 			
		singlepiece = single_segment.segment_text
		leftpiece = left_segment.segment_text
		rightpiece = right_segment.segment_text
			
		# UPDATE THE PARSE
		line.piecesorder_cost += math.log(1 + len(line.pieces), 2)
		line.pieces[coverbrkindex-1] = leftpiece				# i.e., replace singlepiece by leftpiece
		line.breaks.insert(coverbrkindex, attentionpoint)		# or use addcut  
		line.pieces.insert(coverbrkindex, rightpiece)
				 
		# UPDATE GLOBAL COUNTS
		self.totalsegmentcount += 1
		self.split_count += 1
		if left_segment.count == 0 and right_segment.count == 0:
			self.split_2newsegments_count += 1
		elif left_segment.count == 0 or right_segment.count == 0:
			self.split_1newsegment_count += 1
				
		# UPDATE DICTIONARY ENTRIES
		self.decrement_segment_record(single_segment)
		self.increment_segment_record(left_segment)
		self.increment_segment_record(right_segment)


	def update_for_leftsingleton_split(self, line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment, preceding_segment, leftmerged_segment):

		singlepiece = single_segment.segment_text
		leftpiece = left_segment.segment_text
		rightpiece = right_segment.segment_text
		precedingpiece = preceding_segment.segment_text
		leftmergedpiece = leftmerged_segment.segment_text
			
		# UPDATE THE PARSE
		line.pieces[coverbrkindex-2]  = leftmergedpiece		# i.e., replace precedingpiece by leftmergedpiece
		line.pieces[coverbrkindex-1]  = rightpiece
		line.breaks[coverbrkindex-1] += len(leftpiece)		# moves break from beginning of singlepiece over to beginning of rightpiece	[note len(leftpiece) == 1]		
				 											# [note: this break should now be attentionpoint]
		# UPDATE GLOBAL COUNTS
		# Figure this situation as a split plus a merge.
		# self.totalsegmentcount is unchanged
		self.split_count += 1
		self.merge_count += 1
		if left_segment.count == 0 and right_segment.count == 0:
			self.split_2newsegments_count += 1
		elif left_segment.count == 0 or right_segment.count == 0:
			self.split_1newsegment_count += 1
		if leftmerged_segment.count == 0:
			self.merge_newsegment_count += 1

		# UPDATE DICTIONARY ENTRIES
		self.decrement_segment_record(single_segment)
		self.decrement_segment_record(preceding_segment)
		self.increment_segment_record(right_segment)
		self.increment_segment_record(leftmerged_segment)


	def update_for_rightsingleton_split(self, line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment, following_segment, rightmerged_segment):

		singlepiece = single_segment.segment_text
		leftpiece = left_segment.segment_text
		rightpiece = right_segment.segment_text
		followingpiece = following_segment.segment_text
		rightmergedpiece = rightmerged_segment.segment_text
			
		# UPDATE THE PARSE
		line.pieces[coverbrkindex-1] = leftpiece			# i.e., replace singlepiece by leftpiece
		line.pieces[coverbrkindex]   = rightmergedpiece
		line.breaks[coverbrkindex]  -= len(rightpiece)	# moves break from beginning of followingpiece over to beginning of rightmergedpiece	[note len(rightpiece) == 1]		
				 										# [note: this break should now be attentionpoint]		
		# UPDATE GLOBAL COUNTS
		# Figure this situation as a split plus a merge.
		# self.totalsegmentcount is unchanged
		self.split_count += 1
		self.merge_count += 1
		if left_segment.count == 0 and right_segment.count == 0:
			self.split_2newsegments_count += 1
		elif left_segment.count == 0 or right_segment.count == 0:
			self.split_1newsegment_count += 1
		if rightmerged_segment.count == 0:
			self.merge_newsegment_count += 1

		# UPDATE DICTIONARY ENTRIES
		self.decrement_segment_record(single_segment)
		self.decrement_segment_record(following_segment)
		self.increment_segment_record(left_segment)
		self.increment_segment_record(rightmerged_segment)


	def update_for_bothsingletons_split(self, line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment, \
						preceding_segment, following_segment, leftmerged_segment, rightmerged_segment):
						
		singlepiece = single_segment.segment_text
		leftpiece = left_segment.segment_text
		rightpiece = right_segment.segment_text
		precedingpiece = preceding_segment.segment_text
		followingpiece = following_segment.segment_text
		leftmergedpiece = leftmerged_segment.segment_text
		rightmergedpiece = rightmerged_segment.segment_text
		
		# UPDATE THE PARSE
		line.piecesorder_cost -= math.log(len(line.pieces), 2)		
		line.pieces.pop(coverbrkindex-1)							# removes singlepiece
		line.pieces[coverbrkindex-2] = leftmergedpiece			# i.e., replace precedingpiece by leftmergedpiece		
		line.pieces[coverbrkindex-1] = rightmergedpiece		

		#the_break_to_remove = line.breaks[coverbrkindex]
		#line.breaks.remove(the_break_to_remove)
		line.breaks.pop(coverbrkindex)
		line.breaks[coverbrkindex-1] += len(leftpiece)			# moves break from beginning of (former) singlepiece over to beginning of (former) rightpiece		
				 												# [note: this break should now be attentionpoint]
		# UPDATE GLOBAL COUNTS
		# Figure this situation as one split and two merges
		self.totalsegmentcount -= 1
		self.split_count += 1
		self.merge_count += 2
		if left_segment.count == 0 and right_segment.count == 0:	# since leftpiece and rightpiece are both single characters,
			self.split_2newsegments_count += 1						# it's highly unlikely that either would have count == 0
		elif left_segment.count == 0 or right_segment.count == 0:
			self.split_1newsegment_count += 1
		if leftmerged_segment.count == 0:
			self.merge_newsegment_count += 1
		if rightmerged_segment.count == 0:
			self.merge_newsegment_count += 1

		# UPDATE DICTIONARY ENTRIES
		self.decrement_segment_record(single_segment)
		self.decrement_segment_record(preceding_segment)		
		self.decrement_segment_record(following_segment)
		self.increment_segment_record(leftmerged_segment)
		self.increment_segment_record(rightmerged_segment)


	# See previous note about similarity, hence possible reuse, of functions 
	# for Split and Merge operations.

	# MERGING #
	# ----------------------------------------------------------------------------- #
	# FUNCTIONS FOR SAMPLING AMONG LOCAL CONFIGURATIONS WEIGHTED ACCORDING TO COST. #
	# THESE FUNCTIONS APPLY TO DIFFERENT CASES. ALL BEGIN WITH THE WORD 'compare_'. #
	# ----------------------------------------------------------------------------- #
	def compare_bg_simple_merge(self, line, singlepiece, leftpiece, rightpiece, precedingpiece, followingpiece, curr_segment_info, curr_bigram_info, alt_segment_info, alt_bigram_info):
		preceding_segment = curr_segment_info[precedingpiece]
		following_segment = curr_segment_info[followingpiece]
		left_segment   = curr_segment_info[leftpiece]				#if leftpiece == rightpiece, then left_segment and right_segment are the same object
		right_segment  = curr_segment_info[rightpiece]
		single_segment = alt_segment_info[singlepiece]

		#singlepiece = projected_single_segment.segment_text
		#leftpiece   = left_segment.segment_text
		#rightpiece  = right_segment.segment_text
		#precedingpiece = preceding_segment.segment_text
		#followingpiece = following_segment.segment_text

		#k = tuple([precedingpiece, singlepiece])
		#count_list = [v for (k, v) in self.bigram_count_dictionary.items() if k == tuple([precedingpiece, singlepiece])]
		#print("length of count_list:", len(count_list))
		#print("count =", count_list[0])

		#if line.unbroken_text[0:18]  =="thebondissuewillgo":
			#print("compare_bg_simple_merge  LINE PIECES:", line.pieces)
		

		# local contribution to line cost as currently configured
		bigram_for_prec_left  = Bigram(preceding_segment, left_segment, curr_bigram_info[(precedingpiece, leftpiece)])
		bigram_for_left_right = Bigram(left_segment, right_segment, curr_bigram_info[(leftpiece, rightpiece)])
		bigram_for_right_following = Bigram(right_segment, following_segment, curr_bigram_info[(rightpiece, followingpiece)])

		current_contribution = bigram_for_prec_left.get_conditioned_instance_cost()		+ \
							   bigram_for_left_right.get_conditioned_instance_cost()	+ \
							   bigram_for_right_following.get_conditioned_instance_cost()
			
		# alternate configuration
		
		#if (precedingpiece, singlepiece) in self.bigram_count_dictionary:
		#	projected_prec_single_count = 1 + self.bigram_count_dictionary[(precedingpiece, singlepiece)]
		#else:
		#	projected_prec_single_count = 1
		#	
		#if (singlepiece, followingpiece) in self.bigram_count_dictionary:
		#	projected_single_following_count = 1 + self.bigram_count_dictionary[(singlepiece, followingpiece)]
		#else:
		#	projected_single_following_count = 1
			
		bigram_for_prec_single = Bigram(preceding_segment, single_segment, alt_bigram_info[(precedingpiece, singlepiece)])
		bigram_for_single_following = Bigram(single_segment, following_segment, alt_bigram_info[(singlepiece, followingpiece)])
		
		alt_contribution = bigram_for_prec_single.get_conditioned_instance_cost()		+ \
						   bigram_for_single_following.get_conditioned_instance_cost()	- \
						   math.log(len(line.pieces), 2)
		# last addend is adjustment to present value of log(factorial( len(self.pieces) ))

#		# FOR DETERMINISTIC SELECTION, USE THESE LINES 
#		#if alt_contribution < current_contribution:	
#			return 'alt'
#		else
#			return 'current'

		# FOR SAMPLING, USE THESE LINES		
		normalizing_factor = 1.0 / (current_contribution + alt_contribution)
		norm_compl_current = alt_contribution * normalizing_factor
		norm_compl_alt = current_contribution * normalizing_factor
		
		hypothesis_list = [('current', norm_compl_current),  ('alt', norm_compl_alt)]
		selection = weighted_choice(hypothesis_list)

		#if line.unbroken_text[0:18]  =="thebondissuewillgo":
			#print("compare_bg_simple_merge  SELECTION:", selection)
		
		return selection
				

	def compare_simple_merge(self, line, single_segment, left_segment, right_segment):

		# local contribution to line cost as currently configured
		current_contribution = left_segment.get_instance_cost(self.totalsegmentcount)	+  \
							right_segment.get_instance_cost(self.totalsegmentcount)
			
		# alternate configuration
		alt_contribution = single_segment.get_instance_cost(self.totalsegmentcount)	 	-  \
							math.log(len(line.pieces), 2)
		# last addend is adjustment to present value of log(factorial( len(self.pieces) ))

#		# FOR DETERMINISTIC SELECTION, USE THESE LINES 
#		#if alt_contribution < current_contribution:	
#			return 'alt'
#		else
#			return 'current'

		# FOR SAMPLING, USE THESE LINES		
		normalizing_factor = 1.0 / (current_contribution + alt_contribution)
		norm_compl_current = alt_contribution * normalizing_factor
		norm_compl_alt = current_contribution * normalizing_factor
		
		hypothesis_list = [('current', norm_compl_current),  ('alt', norm_compl_alt)]
		selection = weighted_choice(hypothesis_list)
		#print(selection)
		
		return selection
				

	def compare_leftsingleton_merge(self, line, single_segment, left_segment, right_segment, preceding_segment, leftmerged_segment):

		# local contribution to line cost as currently configured
		current_contribution = preceding_segment.get_instance_cost(self.totalsegmentcount)	+ \
							left_segment.get_instance_cost(self.totalsegmentcount)			+ \
							right_segment.get_instance_cost(self.totalsegmentcount)
		
		# alternate configuration
		alt1_contribution = preceding_segment.get_instance_cost(self.totalsegmentcount)		+ \
							single_segment.get_instance_cost(self.totalsegmentcount)		- \
							math.log(len(line.pieces), 2)
		# last addend is adjustment to present value of log(factorial( len(self.pieces) ))

		# another alternate configuration
		alt2_contribution = leftmerged_segment.get_instance_cost(self.totalsegmentcount)	+ \
							right_segment.get_instance_cost(self.totalsegmentcount)			- \
							math.log(len(line.pieces), 2)
		# last addend is adjustment to present value of log(factorial( len(self.pieces) ))


		method = 'sampling'

		# FOR DETERMINISTIC SELECTION, USE THESE LINES
		if method == 'determinate':
			min_contribution = min(current_contribution, alt1_contribution, alt2_contribution)	
			if min_contribution == alt1_contribution:
				return 'alt1'
			elif min_contribution == alt2_contribution:
				return 'alt2'
			else:
				return 'current'
			
		# FOR SAMPLING, USE THESE LINES
		elif method == 'sampling':
			normalizing_factor = 1.0 / (2 * (current_contribution + alt1_contribution + alt2_contribution))
			norm_compl_current = (alt1_contribution + alt2_contribution) * normalizing_factor
			norm_compl_alt1 = (current_contribution + alt2_contribution) * normalizing_factor
			norm_compl_alt2 = (current_contribution + alt1_contribution) * normalizing_factor 
		
			hypothesis_list = [('current',norm_compl_current),  ('alt1',norm_compl_alt1),  ('alt2',norm_compl_alt2)]
			selection = weighted_choice(hypothesis_list)
		
			#print()
			#print("cost_current =", current_contribution, "  cost_alt1 =", alt1_contribution, "  cost_alt2 =", alt2_contribution)
			#print("weight_current =", norm_compl_current, "  weight_alt1 =", norm_compl_alt1, "  weight_alt2 =", norm_compl_alt2)
			#print()
		
			return selection
		

	def compare_rightsingleton_merge(self, line, single_segment, left_segment, right_segment, following_segment, rightmerged_segment):

		# local contribution to line cost as currently configured
		current_contribution = left_segment.get_instance_cost(self.totalsegmentcount)		+ \
							right_segment.get_instance_cost(self.totalsegmentcount)			+ \
							following_segment.get_instance_cost(self.totalsegmentcount)
		
		# alternate configuration
		alt1_contribution = single_segment.get_instance_cost(self.totalsegmentcount)		+ \
							following_segment.get_instance_cost(self.totalsegmentcount)		- \
							math.log(len(line.pieces), 2)
							# last addend is adjustment to present value of log(factorial( len(self.pieces) ))

		# another alternate configuration
		alt2_contribution = left_segment.get_instance_cost(self.totalsegmentcount)			+ \
							rightmerged_segment.get_instance_cost(self.totalsegmentcount)	- \
							math.log(len(line.pieces), 2)
							# last addend is adjustment to present value of log(factorial( len(self.pieces) ))


		method = 'sampling'
							
		# FOR DETERMINISTIC SELECTION, USE THESE LINES
		if method == 'determinate':
			min_contribution = min(current_contribution, alt1_contribution, alt2_contribution)	
			if min_contribution == alt1_contribution:
				return 'alt1'
			elif min_contribution == alt2_contribution:
				return 'alt2'
			else:
				return 'current'
			
		# FOR SAMPLING, USE THESE LINES
		elif method == 'sampling':
			normalizing_factor = 1.0 / (2 * (current_contribution + alt1_contribution + alt2_contribution))
			norm_compl_current = (alt1_contribution + alt2_contribution) * normalizing_factor
			norm_compl_alt1 = (current_contribution + alt2_contribution) * normalizing_factor
			norm_compl_alt2 = (current_contribution + alt1_contribution) * normalizing_factor 
		
			hypothesis_list = [('current',norm_compl_current),  ('alt1',norm_compl_alt1),  ('alt2',norm_compl_alt2)]
			selection = weighted_choice(hypothesis_list)
		
			#print()
			#print("cost_current =", current_contribution, "  cost_alt1 =", alt1_contribution, "  cost_alt2 =", alt2_contribution)
			#print("weight_current =", norm_compl_current, "  weight_alt1 =", norm_compl_alt1, "  weight_alt2 =", norm_compl_alt2)
			#print()
		
			return selection


	def compare_bothsingletons_merge(self, line, single_segment, left_segment, right_segment, preceding_segment, following_segment, leftmerged_segment, rightmerged_segment):
	
		# local contribution to line cost as currently configured
		current_contribution = preceding_segment.get_instance_cost(self.totalsegmentcount) 	+ \
							left_segment.get_instance_cost(self.totalsegmentcount)			+ \
							right_segment.get_instance_cost(self.totalsegmentcount)			+ \
							following_segment.get_instance_cost(self.totalsegmentcount)
		
		# four alternate configurations		
		alt1_contribution = preceding_segment.get_instance_cost(self.totalsegmentcount)		+ \
							single_segment.get_instance_cost(self.totalsegmentcount)		+ \
							following_segment.get_instance_cost(self.totalsegmentcount)		- \
							math.log(len(line.pieces), 2)
							# last addend is adjustment to the current value
							# of  log(factorial( len(self.pieces) ))

		alt2_contribution = leftmerged_segment.get_instance_cost(self.totalsegmentcount)	+ \
							right_segment.get_instance_cost(self.totalsegmentcount)			+ \
							following_segment.get_instance_cost(self.totalsegmentcount)		- \
							math.log(len(line.pieces), 2)
							# last addend is adjustment to the current value
							# of  log(factorial( len(self.pieces) ))

		alt3_contribution = preceding_segment.get_instance_cost(self.totalsegmentcount) 	+ \
							left_segment.get_instance_cost(self.totalsegmentcount)			+ \
							rightmerged_segment.get_instance_cost(self.totalsegmentcount)	- \
							math.log(len(line.pieces), 2)
							# last addend is adjustment to the current value
							# of  log(factorial( len(self.pieces) ))
		
		alt4_contribution = leftmerged_segment.get_instance_cost(self.totalsegmentcount)	+ \
							rightmerged_segment.get_instance_cost(self.totalsegmentcount)	- \
							math.log(len(line.pieces), 2)									- \
							math.log(len(line.pieces)-1, 2)
							# last two addends are adjustment to the current value
							# of  log(factorial( len(self.pieces) ))


		method = 'sampling'

#		# FOR DETERMINISTIC SELECTION, USE THESE LINES
		if method == 'determinate':
			min_contribution = min(current_contribution, alt1_contribution, alt2_contribution, alt3_contribution, alt4_contribution)	
			if min_contribution == alt1_contribution:
				return 'alt1'
			elif min_contribution == alt2_contribution:
				return 'alt2'
			elif min_contribution == alt3_contribution:
				return 'alt3'
			elif min_contribution == alt4_contribution:
				return 'alt4'
			else:
				return 'current'
			
		# FOR SAMPLING, USE THESE LINES
		elif method == 'sampling':
			sum = current_contribution + alt1_contribution + alt2_contribution + alt3_contribution + alt4_contribution
			normalizing_factor = 1.0 / (4 * sum)

			norm_compl_current = (sum - current_contribution) * normalizing_factor
			norm_compl_alt1 = (sum - alt1_contribution) * normalizing_factor
			norm_compl_alt2 = (sum - alt2_contribution) * normalizing_factor 
			norm_compl_alt3 = (sum - alt3_contribution) * normalizing_factor
			norm_compl_alt4 = (sum - alt4_contribution) * normalizing_factor 
		
			hypothesis_list = [ ('current',norm_compl_current),  
								('alt1',norm_compl_alt1),  
								('alt2',norm_compl_alt2),
								('alt3',norm_compl_alt3),  
								('alt4',norm_compl_alt4) ]

			selection = weighted_choice(hypothesis_list)
		
			return selection


	# MERGING #		
	# ---------------------------------------------------------------------------- #
	# FUNCTIONS FOR UPDATING RECORDS ACCORDING TO SELECTED PARSING MODIFICATIONS.  #
	# THESE FUNCTIONS APPLY TO DIFFERENT CASES. ALL BEGIN WITH THE WORD 'update_'. #
	# ---------------------------------------------------------------------------- #
	def update_for_bg_simple_merge(self, line, attentionpoint, coverbrkindex, singlepiece, leftpiece, rightpiece, precedingpiece, followingpiece, curr_segment_info, curr_bigram_info, alt_segment_info, alt_bigram_info): 			
		preceding_segment = curr_segment_info[precedingpiece]
		following_segment = curr_segment_info[followingpiece]
		left_segment   = curr_segment_info[leftpiece]				#if leftpiece == rightpiece, then left_segment and right_segment are the same object
		right_segment  = curr_segment_info[rightpiece]
		single_segment = alt_segment_info[singlepiece]

		#singlepiece = projected_single_segment.segment_text
		#leftpiece   = left_segment.segment_text
		#rightpiece  = right_segment.segment_text
		#precedingpiece = preceding_segment.segment_text
		#followingpiece = following_segment.segment_text
			
		#if line.unbroken_text[0:18]  =="thebondissuewillgo":
			#print("update_for_bg_simple_merge")
			#print("singlepiece =", singlepiece)
			#print("leftpiece =", leftpiece)
			#print("rightpiece =", rightpiece)
			#print("precedingpiece =", precedingpiece)
			#print("followingpiece =", followingpiece)
		

		# UPDATE THE PARSE
		line.piecesorder_cost -= math.log(len(line.pieces), 2)
		line.pieces[coverbrkindex-1] = singlepiece				# i.e., replace leftpiece by singlepiece
		line.breaks.pop(coverbrkindex)
		line.pieces.pop(coverbrkindex)
				 
		# UPDATE GLOBAL COUNTS
		self.totalsegmentcount -= 1
		self.merge_count += 1
		if single_segment.count == 1:
			self.merge_newsegment_count += 1
				
		# UPDATE DICTIONARY ENTRIES
		self.increment_segment_record_bg(single_segment)
		self.decrement_segment_record(left_segment)
		self.decrement_segment_record(right_segment)
		
		self.decrement_bigram_record((precedingpiece, leftpiece))
		self.decrement_bigram_record((leftpiece, rightpiece))
		self.decrement_bigram_record((rightpiece, followingpiece))
		self.increment_bigram_record((precedingpiece, singlepiece))
		self.increment_bigram_record((singlepiece, followingpiece))

		#if '#' in self.segment_object_dictionary:
			#print("At end of build_dictionaries, '#' is in dictionary")
			#print("um:YES")
		#else:
			#print("At end of build_dictionaries, '#' is NOT in dictionary")
			#print("um:NO")
		


	def update_for_simple_merge(self, line, attentionpoint, coverbrkindex, single_segment, left_segment, right_segment): 			
		singlepiece = single_segment.segment_text
		leftpiece = left_segment.segment_text
		rightpiece = right_segment.segment_text
			
		# UPDATE THE PARSE
		line.piecesorder_cost -= math.log(len(line.pieces), 2)
		line.pieces[coverbrkindex-1] = singlepiece				# i.e., replace leftpiece by singlepiece
		line.breaks.pop(coverbrkindex)
		line.pieces.pop(coverbrkindex)
				 
		# UPDATE GLOBAL COUNTS
		self.totalsegmentcount -= 1
		self.merge_count += 1
		if single_segment.count == 0:
			self.merge_newsegment_count += 1
				
		# UPDATE DICTIONARY ENTRIES
		self.increment_segment_record(single_segment)
		self.decrement_segment_record(left_segment)
		self.decrement_segment_record(right_segment)


	def update_for_leftsingleton_merge(self, line, attentionpoint, coverbrkindex, left_segment, preceding_segment, leftmerged_segment):
	
		leftpiece = left_segment.segment_text
		precedingpiece = preceding_segment.segment_text
		leftmergedpiece = leftmerged_segment.segment_text
			
		# UPDATE THE PARSE
		line.piecesorder_cost -= math.log(len(line.pieces), 2)
		line.pieces[coverbrkindex-2]  = leftmergedpiece		# i.e., replace precedingpiece by leftmergedpiece
		line.pieces.pop(coverbrkindex-1)
		line.breaks.pop(coverbrkindex-1)

		# UPDATE GLOBAL COUNTS
		self.totalsegmentcount -= 1
		self.merge_count += 1
		if leftmerged_segment.count == 0:
			self.merge_newsegment_count += 1

		# UPDATE DICTIONARY ENTRIES
		self.increment_segment_record(leftmerged_segment)
		self.decrement_segment_record(preceding_segment)
		self.decrement_segment_record(left_segment)


	def update_for_rightsingleton_merge(self, line, attentionpoint, coverbrkindex, right_segment, following_segment, rightmerged_segment):

		rightpiece = right_segment.segment_text
		followingpiece = following_segment.segment_text
		rightmergedpiece = rightmerged_segment.segment_text
			
		# UPDATE THE PARSE
		line.piecesorder_cost -= math.log(len(line.pieces), 2)
		line.pieces[coverbrkindex] = rightmergedpiece			# i.e., replace rightpiece by rightmergedpiece
		line.pieces.pop(coverbrkindex+1)  
		line.breaks.pop(coverbrkindex+1)

		# UPDATE GLOBAL COUNTS
		self.totalsegmentcount -= 1
		self.merge_count += 1
		if rightmerged_segment.count == 0:
			self.merge_newsegment_count += 1

		# UPDATE DICTIONARY ENTRIES
		self.increment_segment_record(rightmerged_segment)
		self.decrement_segment_record(right_segment)
		self.decrement_segment_record(following_segment)


	def update_for_bothsingletons_merge(self, line, attentionpoint, coverbrkindex, left_segment, right_segment, \
						preceding_segment, following_segment, leftmerged_segment, rightmerged_segment):
						
		leftpiece = left_segment.segment_text
		rightpiece = right_segment.segment_text
		precedingpiece = preceding_segment.segment_text
		followingpiece = following_segment.segment_text
		leftmergedpiece = leftmerged_segment.segment_text
		rightmergedpiece = rightmerged_segment.segment_text
		
		# UPDATE THE PARSE
		line.piecesorder_cost -= ( math.log(len(line.pieces), 2) + math.log(len(line.pieces)-1, 2) )
		line.pieces.pop(coverbrkindex+1)							# removes followingpiece
		line.pieces.pop(coverbrkindex)							# removes rightpiece
		line.pieces[coverbrkindex-1] = rightmergedpiece			# i.e., replace leftpiece by rightmergedpiece		
		line.pieces[coverbrkindex-2] = leftmergedpiece			# i.e., replace precedingpiece by leftmergedpiece		
		line.breaks.pop(coverbrkindex+1)
		line.breaks.pop(coverbrkindex-1)

		# UPDATE GLOBAL COUNTS
		# Figure this situation as two merges
		self.totalsegmentcount -= 2
		self.merge_count += 2
		if leftmerged_segment.count == 0:
			self.merge_newsegment_count += 1
		if rightmerged_segment.count == 0:
			self.merge_newsegment_count += 1

		# UPDATE DICTIONARY ENTRIES
		self.increment_segment_record(leftmerged_segment)
		self.increment_segment_record(rightmerged_segment)
		self.decrement_segment_record(preceding_segment)		
		self.decrement_segment_record(following_segment)
		self.decrement_segment_record(left_segment)
		self.decrement_segment_record(right_segment)


##########################
	def decrement_segment_record(self, this_segment):
		segtext = this_segment.segment_text
		
		this_segment.count -= 1
		if this_segment.count == 0:
			del self.segment_object_dictionary[segtext]
			if segtext in self.true_segment_dictionary:		# additional info; no contribution to processing
				self.deletedandtrue_devcount += 1
				self.deletedandtrue_dictionary[segtext] = self.true_segment_dictionary[segtext]
		else:
			this_segment.divide_charges_among_instances()
			this_segment.plog = this_segment.get_plog(self.totalsegmentcount)		
	
	def increment_segment_record(self, this_segment):
		segtext = this_segment.segment_text
		
		if segtext not in self.segment_object_dictionary:
			self.segment_object_dictionary[segtext] = this_segment
			if segtext in self.true_segment_dictionary:		# additional info; no contribution to processing
				self.addedandtrue_devcount += 1
				self.addedandtrue_dictionary[segtext] = self.true_segment_dictionary[segtext]
		self.segment_object_dictionary[segtext].count += 1
		self.segment_object_dictionary[segtext].divide_charges_among_instances()
		self.segment_object_dictionary[segtext].plog = self.segment_object_dictionary[segtext].get_plog(self.totalsegmentcount)

	def increment_segment_record_bg(self, projected_segment):
		segtext = projected_segment.segment_text		
		if segtext not in self.segment_object_dictionary:
			if segtext in self.true_segment_dictionary:		# additional info; no contribution to processing
				self.addedandtrue_devcount += 1
				self.addedandtrue_dictionary[segtext] = self.true_segment_dictionary[segtext]
				
		self.segment_object_dictionary[segtext] = projected_segment   # the updated count and dependent values were built into the projected version 
				
		#self.segment_object_dictionary[segtext].count += 1
		#self.segment_object_dictionary[segtext].divide_charges_among_instances()
		#self.segment_object_dictionary[segtext].plog = self.segment_object_dictionary[segtext].get_plog(self.totalsegmentcount)
		
	def decrement_bigram_record(self, textpair):
		self.bigram_count_dictionary[textpair] -= 1
		if self.bigram_count_dictionary[textpair] == 0:
			del self.bigram_count_dictionary[textpair]
	
	def increment_bigram_record(self, textpair):
		if not textpair in self.bigram_count_dictionary:
			self.bigram_count_dictionary[textpair] = 1
		else:
			self.bigram_count_dictionary[textpair] += 1
		
##########################

	def lrparse_line_bg(self, line, longest_dictionary_entry_length, outfile  ):	 	# from wordbreaker.py: ParseWord()   Needs different name.  outfile is for verbose (mostly --last part always prints).
         
        # <---- outerscan range----------------------------------------------------> #
        #              starting point----^                           ^---outerscan
        #                                <--------chunkstart range-->
		#                         chunkstart---^
        #                                      <------chunk--------->


		#verboseflag = (line.unbroken_text[0:10] == "whosoeverv")   #iolatesourrooftree,thelegendstates,canexpectmaximalsorrow.
		verboseflag = (line.unbroken_text[0:24] == "additionisindicatedbythe")
		
		#verboseflag = False		# False	 # True
		if verboseflag: print("\n", file=outfile)
		if verboseflag: print(line.unbroken_text, file=outfile)
		if verboseflag:	print("Outer\tInner", file=outfile)
		if verboseflag:	print("scan:\tscan:\tChunk\tFound?", file=outfile)		# column headers

		linelength = len(line.unbroken_text)

		parse2here=dict()			# key is an int < linelength, value is a list of pieces
		parse2here[0] = []			# empty list

		bestcost2here = dict()		# key is an int < linelength, value is a sum of segment costs + ordercost for that many segments
		bestcost2here[0] = 0

		for outerscan in range(1,linelength+1):   
			# Note: at this point in the computation, 
        	# the values of parse2here[x] and bestcost2here[x] are known for all x < outerscan.  
			# The purpose of this pass is to calculate these values for x = outerscan.

			parse2here[outerscan] = list()

			# CONSIDER CHUNK TO EXTEND A SHORTER PREVIOUSLY-OBTAINED PARSE UP TO CURRENT VALUE OF outerscan.
			# CHECK ALL POSSIBLE CHUNK START POINTS. KEEP TRACK TO FIND THE PARSE WITH LOWEST COST.
			startingpoint = max(0, outerscan - longest_dictionary_entry_length)
			howmanyspaces = -1					# This variable is for formatting. 
			chosen_cost = FLOAT_INF				# MUST BE SURE TOTAL_COST IS POPULATED  OOPS - use FLOAT_INF instead
			chosen_chunk = line.unbroken_text
			chosen_chunkstart = startingpoint	# MIGHT BE MORE CONSISTENT TO STEP BACKWARDS  set to outerscan-1 ??
			
 			# ALL CHUNKS HAVE SAME RIGHT ENDPOINT (outerscan-1)
            # START WITH FIRST POSSIBLE CHUNK (the chunk with left endpoint at startingpoint)
			# LOOP THROUGH SUCCEEDING CHUNK START POINTS
            # WOULD BACKWARDS BE CLEARER? INSTEAD OF startingpoint, CALL IT limitpoint?
			for chunkstart in range(startingpoint, outerscan):
				chunk = line.unbroken_text[chunkstart: outerscan]
				if verboseflag: print("\n %3s\t%3s  " % (outerscan, chunkstart), end=" ", file=outfile)

				if chunk not in self.segment_object_dictionary:
					continue

				else:
					howmanyspaces +=1
					if verboseflag: 
						for x in range(howmanyspaces):
							print(" ", end="", file=outfile)
					if verboseflag:	print("  %s"% chunk, end=" ", file=outfile)
					
					if verboseflag: print("   %5s" % "Yes.", end=" ", file=outfile)
					chunk_segment = self.fetch_plogged_segment_from_dictionary(chunk)

					# build the bigram object
					if chunkstart == 0:
						backpiece = '#'
						backsegment = self.lineboundary_segment
					else:
						parse2chunkstart = parse2here[chunkstart]	# best parse as far as chunkstart
						backpiece = parse2chunkstart[-1]			# last piece in the list
						
						if not (backpiece in self.segment_object_dictionary):
							continue
						else:
							backsegment = self.fetch_plogged_segment_from_dictionary(backpiece)
					
					if (backpiece, chunk) in self.bigram_count_dictionary:
						backpiece_chunk_count = self.bigram_count_dictionary[(backpiece, chunk)]
					else:
						backpiece_chunk_count = 1		
						
					this_bigram = Bigram(backsegment, chunk_segment, backpiece_chunk_count)
					chunk_cost = this_bigram.get_conditioned_instance_cost()
				
					testcost = bestcost2here[chunkstart] + chunk_cost + \
							   math.log( 1 + len(parse2here[chunkstart]), 2 )
							   #math.log( math.factorial( 1 + len(parse2here[chunkstart]) ), 2)
					#print(" %7.3f bits" % (testcost), "= %7.3f" % (bestcost2here[chunkstart]), "+ %7.3f" % (chunk_cost), "+ %7.3f" % (math.log( math.factorial( 1 + len(parse2here[chunkstart]) ), 2)) )
					if verboseflag: print(" %7.3f bits" % (testcost), end=" ", file=outfile)				
					if verboseflag: print("   %s" % parse2here[chunkstart], end=" ", file=outfile)	# put this at end of line due to spacing
				
					if testcost < chosen_cost:
						chosen_cost = testcost
						chosen_chunk = chunk
						chosen_chunkstart = chunkstart
					
			bestcost2here[outerscan] = chosen_cost
			
			parse2here[outerscan] = list(parse2here[chosen_chunkstart])		# makes a copy
			parse2here[outerscan].append(chosen_chunk)

			#if verboseflag: print("\n\t\t\t\t\t\t\t\t\tchosen:", chosen_chunk, end=" ", file=outfile)
			if verboseflag: print("\nchosen:", chosen_chunk, end=" ", file=outfile)
			if verboseflag: print("  parse [0, %d)" % outerscan, "= %s " % parse2here[outerscan], end=" ", file=outfile)
			if verboseflag: print("\n", file=outfile)
		

		parsed_line = parse2here[linelength]		# IS IT linelength-1  OR  linelength?  ANSWER: linelength
		bitcost = bestcost2here[linelength]

		print("\n%7.3f\t" % line.total_cost, end="", file=outfile)		# How to get this right-aligned?
		for piece in line.pieces:
			print(" %s" % piece, end="", file=outfile)
		print(file=outfile)
		
		print("%7.3f\t" % bitcost, end="", file=outfile)				# Here also.        
		for chunk in parsed_line:
			print(" %s" % chunk, end="", file=outfile)
		print("\n", file=outfile)


		return (parsed_line, bitcost)


	# THIS IS THE UNIGRAM VERSION. THE BIGRAM VERSION IS ABOVE !!!	
	def lrparse_line(self, line, longest_dictionary_entry_length, outfile  ):	 	# from wordbreaker.py: ParseWord()   Needs different name.  outfile is for verbose (mostly --last part always prints).
         
        # <---- outerscan range----------------------------------------------------> #
        #              starting point----^                           ^---outerscan
        #                                <--------chunkstart range-->
		#                         chunkstart---^
        #                                      <------chunk--------->


		verboseflag = False		# False	 # True
		if verboseflag: print("\n", file=outfile)
		if verboseflag: print(line.unbroken_text, file=outfile)
		if verboseflag:	print("Outer\tInner", file=outfile)
		if verboseflag:	print("scan:\tscan:\tChunk\tFound?", file=outfile)		# column headers

		linelength = len(line.unbroken_text)

		parse2here=dict()			# key is an int < linelength, value is a list of pieces
		parse2here[0] = []			# empty list

		bestcost2here = dict()		# key is an int < linelength, value is a sum of segment costs + ordercost for that many segments
		bestcost2here[0] = 0

		for outerscan in range(1,linelength+1):   
			# Note: at this point in the computation, 
        	# the values of parse2here[x] and bestcost2here[x] are known for all x < outerscan.  
			# The purpose of this pass is to calculate these values for x = outerscan.

			parse2here[outerscan] = list()

			# CONSIDER CHUNK TO EXTEND A SHORTER PREVIOUSLY-OBTAINED PARSE UP TO CURRENT VALUE OF outerscan.
			# CHECK ALL POSSIBLE CHUNK START POINTS. KEEP TRACK TO FIND THE PARSE WITH LOWEST COST.
			startingpoint = max(0, outerscan - longest_dictionary_entry_length)
			howmanyspaces = -1					# This variable is for formatting. 
			chosen_cost = FLOAT_INF				# MUST BE SURE TOTAL_COST IS POPULATED  OOPS - use FLOAT_INF instead
			chosen_chunk = line.unbroken_text
			chosen_chunkstart = startingpoint	# MIGHT BE MORE CONSISTENT TO STEP BACKWARDS  set to outerscan-1 ??
			
 			# ALL CHUNKS HAVE SAME RIGHT ENDPOINT (outerscan-1)
            # START WITH FIRST POSSIBLE CHUNK (the chunk with left endpoint at startingpoint)
			# LOOP THROUGH SUCCEEDING CHUNK START POINTS
            # WOULD BACKWARDS BE CLEARER? INSTEAD OF startingpoint, CALL IT limitpoint?
			for chunkstart in range(startingpoint, outerscan):
				chunk = line.unbroken_text[chunkstart: outerscan]
				if verboseflag: print("\n %3s\t%3s  " % (outerscan, chunkstart), end=" ", file=outfile)

				if chunk not in self.segment_object_dictionary:
					continue

				else:
					howmanyspaces +=1
					if verboseflag: 
						for x in range(howmanyspaces):
							print(" ", end="", file=outfile)
					if verboseflag:	print("  %s"% chunk, end=" ", file=outfile)
					
					if verboseflag: print("   %5s" % "Yes.", end=" ", file=outfile)
					chunk_segment = self.fetch_plogged_segment_from_dictionary(chunk)
					chunk_cost = chunk_segment.get_instance_cost(self.totalsegmentcount)
				
					testcost = bestcost2here[chunkstart] + chunk_cost + \
							   math.log( 1 + len(parse2here[chunkstart]), 2 )
							   #math.log( math.factorial( 1 + len(parse2here[chunkstart]) ), 2)
					#print(" %7.3f bits" % (testcost), "= %7.3f" % (bestcost2here[chunkstart]), "+ %7.3f" % (chunk_cost), "+ %7.3f" % (math.log( math.factorial( 1 + len(parse2here[chunkstart]) ), 2)) )
					if verboseflag: print(" %7.3f bits" % (testcost), end=" ", file=outfile)				
					if verboseflag: print("   %s" % parse2here[chunkstart], end=" ", file=outfile)	# put this at end of line due to spacing
				
					if testcost < chosen_cost:
						chosen_cost = testcost
						chosen_chunk = chunk
						chosen_chunkstart = chunkstart
					
			bestcost2here[outerscan] = chosen_cost
			
			parse2here[outerscan] = list(parse2here[chosen_chunkstart])		# makes a copy
			parse2here[outerscan].append(chosen_chunk)

			#if verboseflag: print("\n\t\t\t\t\t\t\t\t\tchosen:", chosen_chunk, end=" ", file=outfile)
			if verboseflag: print("\nchosen:", chosen_chunk, end=" ", file=outfile)
			if verboseflag: print("  parse [0, %d)" % outerscan, "= %s " % parse2here[outerscan], end=" ", file=outfile)
			if verboseflag: print("\n", file=outfile)
		

		parsed_line = parse2here[linelength]		# IS IT linelength-1  OR  linelength?  ANSWER: linelength
		bitcost = bestcost2here[linelength]

		print("\n%7.3f\t" % line.total_cost, end="", file=outfile)		# How to get this right-aligned?
		for piece in line.pieces:
			print(" %s" % piece, end="", file=outfile)
		print(file=outfile)
		
		print("%7.3f\t" % bitcost, end="", file=outfile)				# Here also.        
		for chunk in parsed_line:
			print(" %s" % chunk, end="", file=outfile)
		print("\n", file=outfile)


		return (parsed_line, bitcost)


	def compute_bg_brokenline_cost(self, line):	
		line.total_cost = 0.0							# should already be set by __init__
		
		backpiece = '#'
		backsegment = self.lineboundary_segment
		for piece in line.pieces:
			if piece in self.segment_object_dictionary:
				piece_segment = self.fetch_plogged_segment_from_dictionary(piece)
			else:
				piece_segment = self.new_segment_object(piece, 1)			# 0 or 1 ??--CURRENTLY 1, SO NO PENALTYFACTOR  2016_04_04
																			# only happens in test_unbroken_text()

			if (backpiece, piece) in self.bigram_count_dictionary:
				backpiece_piece_count = self.bigram_count_dictionary[(backpiece, piece)]
			else:
				backpiece_piece_count = 1		


			this_bigram = Bigram(backsegment, piece_segment, backpiece_piece_count)	
				
			piece_cost = this_bigram.get_conditioned_instance_cost()
			line.total_cost += piece_cost
			
			backpiece = piece
			backsegment = piece_segment

		line.piecesorder_cost =  math.log (math.factorial(len(line.pieces)), 2)
		line.total_cost += line.piecesorder_cost

	def compute_brokenline_cost(self, line):	
		line.total_cost = 0.0							# should already be set by __init__		
		for piece in line.pieces:
			if piece in self.segment_object_dictionary:
				this_segment = self.fetch_plogged_segment_from_dictionary(piece)
			else:
				this_segment = self.new_segment_object(piece, 0)
				
			piece_cost = this_segment.get_instance_cost(self.totalsegmentcount)
			line.total_cost += piece_cost

		line.piecesorder_cost =  math.log (math.factorial(len(line.pieces)), 2)
		line.total_cost += line.piecesorder_cost



	def populate_line_displaylists(self, line):	
		self.count_list					= []		# List of segment counts, in proper order.
		self.phonocost_portion_list 	= []		# List per segment of phonocost_portion, in proper order. Similarly for other list variables.
		self.ordercost_portion_list     = []		# The lists are used to arrange segment information attractively for display.
		self.inclusioncost_portion_list = []		# Are they useful to retain? Should they be in a separate Display class?
		self.plog_list 		            = []
		self.subtotal_list              = []		# list per segment of following quantity: 
		for piece in line.pieces:
			if piece in self.segment_object_dictionary:
				this_segment = self.fetch_plogged_segment_from_dictionary(piece)
			else:
				this_segment = self.new_segment_object(piece, 0)

				
			piece_cost = this_segment.get_instance_cost(self.totalsegmentcount)
				
			# THESE LIST VARIABLES EXIST FOR DISPLAY ONLY  [expect changes if class structure is reworked]
			line.count_list.append(this_segment.count)
			line.plog_list.append(this_segment.get_plog_charge(self.totalsegmentcount))  #(PLOGCOEFF * this_instance.plog)
			line.phonocost_portion_list.append(this_segment.phonocost_portion)	
			line.ordercost_portion_list.append(this_segment.ordercost_portion)	
			line.inclusioncost_portion_list.append(this_segment.inclusioncost_portion)
			line.subtotal_list.append(piece_cost) 		


	def rebase_bg(self, verbose_outfile):
		
		# REPARSE
		longest = 0
		for piece in self.segment_object_dictionary:
			if len(piece) > longest:
				longest = len(piece)
		print("longest_entry_length =", longest)
		print("longest_entry_length =", longest, file=verbose_outfile)
		
		print("parsing...")
		for ln in self.line_object_list:
			#(parsed_line, bitcost) = self.lrparse_line(ln, longest, verbose_outfile)
			(parsed_line, bitcost) = self.lrparse_line_bg(ln, longest, verbose_outfile)
			ln.pieces = list(parsed_line)		# copy
			ln.populate_breaks_from_pieces()
			#ln.total_cost = bitcost  [stored for comparison in RECOMPUTE section]
			
			# ln.pieces.append("#")


		# RECOUNT SEGMENTS
		# rebuild the dictionary   IS THERE ANYTHING ELSE THAT NEEDS TO BE REINITED ????
		print("updating segment and bigram counts...")
		self.build_dictionaries_from_pieces()
		
#		self.segment_object_dictionary = {}
#		self.bigram_object_dictionary = {}
#		self.totalsegmentcount = 0
#				
#		for ln in self.line_object_list:
#			backpiece = "#"
#			for piece in ln.pieces:
#				self.totalsegmentcount += 1								# ALERT - for any item in or about to go into the dictionary,
#				if not piece in self.segment_object_dictionary:			# increment totalsegmentcount BEFORE populating its plog variable		  
#					self.segment_object_dictionary[piece] = self.new_segment_object(piece, 1)
#				else:
#					self.segment_object_dictionary[piece].count += 1
		
#				bigram = (backpiece, piece)
#				if not bigram in self.bigram_dictionary:
#					self.bigram_dictionary[bigram] = 1
#				else:
#					self.bigram_dictionary[bigram] += 1
#				backpiece = piece

#			IS THIS NEEDED? probably not
#			lastpiece = ln.pieces[-1]
#			bigram = (lastpiece, "#")
#			if not bigram in self.bigram_dictionary:
#				self.bigram_dictionary[bigram] = 1
#			else:
#				self.bigram_dictionary[bigram] += 1

#		# fill in the information that depends on the count	 
#		for sgmt in self.segment_object_dictionary.values():
#			sgmt.divide_charges_among_instances()
#			sgmt.get_plog(self.totalsegmentcount)


		# RECOMPUTE
		print("computing line costs...")
		self.overall_cost = 0.0
		for ln in self.line_object_list:
			for piece in ln.pieces:
				assert(piece in self.segment_object_dictionary)		# there should be no "new" pieces
			#self.compute_brokenline_cost(ln)
			self.compute_bg_brokenline_cost(ln)
			self.overall_cost += ln.total_cost



	def load_truth_and_data(self, true_line, line_object):		# from wordbreaker code
		unbroken_text_construction = ""
		true_breaks_construction = list()
		true_breaks_construction.append(0)						# always put a break at the beginning

		# Clean up data as desired
		true_line = true_line.casefold()
		true_line = true_line.replace(".", " . ")				# these characters will go into TrueDictionary as separate words
		true_line = true_line.replace(",", " , ")
		true_line = true_line.replace(";", " ; ")
		true_line = true_line.replace("!", " ! ")
		true_line = true_line.replace("?", " ? ")
		true_line = true_line.replace(":", " : ")
		true_line = true_line.replace(")", " ) ")
		true_line = true_line.replace("(", " ( ")

		pieces_list = true_line.split()							# split true_line into pieces
		if len(pieces_list) <=	1:								# punctuation only. 10 such lines in Brown corpus.
			return
		#pieces_list.append("\n")								# added only to match previous runs; may prefer without. ATTN: outfile_corpuslines, outfile_lrparse
		for piece in pieces_list:
			self.true_totalsegmentcount += 1					# Record in TrueDictionary
			if piece not in self.true_segment_dictionary:
				self.true_segment_dictionary[piece] = 1
			else:
				self.true_segment_dictionary[piece] += 1

			unbroken_text_construction += piece					# Build up unbroken line
			true_breaks_construction.append(len(unbroken_text_construction))
		
		line_object.unbroken_text = unbroken_text_construction
		line_object.true_text = true_line
		line_object.true_breaks = true_breaks_construction
		self.line_object_list.append(line_object)
	
	
	
	def precision_recall(self):		# from wordbreaker

		# the following calculations are precision and recall *for breaks* (not for morphemes)
		true_positives = 0
		for line in self.line_object_list:            
			line_true_positives = len(set(line.breaks).intersection(set(line.true_breaks))) - 1		# IMPORTANT - This removes the zero breakpoint
			true_positives += line_true_positives

		self.break_precision = float(true_positives) /  self.totalsegmentcount
		self.break_recall    = float(true_positives) /  self.true_totalsegmentcount

		#formatstring = "%16s %12s %6.4f %9s %6.4f"
		#print()
		#print(formatstring %( "Break based word", "precision", self.break_precision, "recall", self.break_recall))
        #print(formatstring %( "Break based word", "precision", break_precision, "recall", break_recall), file=outfile)


        # Token_based precision for word discovery:
		if True:
			true_positives = 0
			for piece in self.segment_object_dictionary:
				if piece in self.true_segment_dictionary:
					these_true_positives = min(self.true_segment_dictionary[piece], self.segment_object_dictionary[piece].count)
				else:
					these_true_positives = 0
				true_positives += these_true_positives

			self.token_precision = float(true_positives) / self.totalsegmentcount
			self.token_recall    = float(true_positives) / self.true_totalsegmentcount

			#print(formatstring %( "Token_based word", "precision", word_precision, "recall", word_recall), file=outfile)
			#print(formatstring %( "Token_based word", "precision", word_precision, "recall", word_recall))


		# Type_based precision for word discovery:
		if True:
			true_positives = 0
			for piece in self.segment_object_dictionary:
				if piece in self.true_segment_dictionary:
					true_positives +=1

			self.dictionary_precision = float(true_positives) / len(self.segment_object_dictionary)
			self.dictionary_recall    = float(true_positives) / len(self.true_segment_dictionary)

			#print >>outfile, "\n\n***\n"
			#print "Type_based Word Precision  %6.4f; Word Recall  %6.4f" %(word_precision ,word_recall)
			#print(formatstring %( " Type_based word", "precision", word_precision, "recall", word_recall), file=outfile)
			#print(formatstring %( " Type_based word", "precision", word_precision, "recall", word_recall))



	def output_stats(self, outfile, loopno, show_cost):
		if (loopno % REBASE_PERIOD == 0):
			print()
			print(file=outfile)		

		formatstring = "%4d   S:%4d   M:%4d   new:%2d %2d   %3d    At:%4d   Dt:%4d      BP: %6.4f   BR: %6.4f         TP: %6.4f   TR: %6.4f         DP: %6.4f   DR: %6.4f"

		filled_string = formatstring % (loopno,		
				self.split_count,
				self.merge_count,  
				self.split_1newsegment_count, 
		        self.split_2newsegments_count,
		        self.merge_newsegment_count,
		        
		        self.addedandtrue_devcount,
		        self.deletedandtrue_devcount,

		        self.break_precision,
		        self.break_recall,
		        self.token_precision,
		        self.token_recall,
		        self.dictionary_precision,
		        self.dictionary_recall)
		        
		cost_string = ""
		if show_cost == True:
			cost_string = "      COST = %.4f" % self.overall_cost
			#number_with_commas = "{0:,.4f}".format(self.overall_cost)
			#cost_string = "      COST = %s" % number_with_commas
    		        
		print( filled_string + cost_string)
		print( filled_string + cost_string, file=outfile)


	
	def test_unbroken_text(self, text):		# ALERT - THIS HAS NOT BEEN MODIFIED FOR BIGRAM APPROACH
		print("\npoint = 0 (i.e., unbroken text)")		
		test_parse = Line(text)
		test_parse.breaks = [0, len(text)]
		test_parse.pieces.append(text)

		self.compute_brokenline_cost(test_parse)
		self.populate_line_displaylists(test_parse)
		bestscore = test_parse.total_cost
		bestlocation = 0
		test_parse.displaytoscreen_detail()
	
		for point in range(1, len(text)):
			print("\npoint =", point)
			test_parse = Line(text)
			test_parse.breaks = [0, point, len(text)]
			test_parse.pieces.append(text[0:point])
			test_parse.pieces.append(text[point:])

			self.compute_brokenline_cost(test_parse)
			self.populate_line_displaylists(test_parse)
			if test_parse.total_cost < bestscore:
				bestscore = test_parse.total_cost
				bestlocation = point
			test_parse.displaytoscreen_detail()

		print("\nBest score = ", bestscore, "at point = ", bestlocation, "\n")    # FORMAT bestscore AS %8.1f

## ---------------------------------------------------------------------------------------##
##		End of class Document
## ---------------------------------------------------------------------------------------#


def weighted_choice(hypothesis_list):
	samplepoint = random.random()
	#print("In weighted_choice function, samplepoint =", samplepoint)
	cum = 0.0
	for (hyp, weight) in hypothesis_list:
		cum += weight
		#print("cum =", cum)
		if samplepoint < cum:
			#print("returning hyp:", hyp)
			return hyp
	return hyp


def	save_state_to_file(loopno, pkl_outfile_name, document_object):
	if g_encoding == "utf8":
		pkl_outfile = codecs.open(pkl_outfile_name, encoding =  "utf-8", mode = 'w',)
	else:
		pkl_outfile = open(pkl_outfile_name, mode='w')

	# Header for jsonpickle outfile
	i = datetime.datetime.now()
	print("# Date = " + i.strftime("%Y_%m_%d"), file=pkl_outfile)
	print("# Time = " + i.strftime("%H_%M"), file=pkl_outfile)
	print(file=pkl_outfile)

	print("#----------------------------------------\n# Loop number:", loopno, file=pkl_outfile)
	print("#----------------------------------------", file=pkl_outfile)	
	print("serializing...")
	serialstr = jsonpickle.encode(document_object, keys=True)
	print("printing serialization to file...")
	print(serialstr, file=pkl_outfile)
	
	pkl_outfile.close()


def load_state_from_file(pkl_infile_name):
	if g_encoding == "utf8":
		pkl_infile = codecs.open(pkl_infile_name, encoding = 'utf-8')
	else:
		pkl_infile = open(pkl_infile_name) 

	print("Loading saved state...")
	filelines = pkl_infile.readlines()
	serialstr = filelines[-1]
	#print(serialstr[0:40])
	document = jsonpickle.decode(serialstr, keys=True)

	pkl_infile.close()
	return document


#----------------------------------------------------------------------------------#
# this is not currently being used: 
# #def ShiftBreak (word, thiswordbreaks, shiftamount, outfile, totalmorphemecount):
# Code for this fuction is available in earlier versions in the git repository.
#----------------------------------------------------------------------------------#



#--------------------------------------------------------------------##
#		Main program    
#       (This will be revised to conform to lxa2015 approach.)
#--------------------------------------------------------------------##

#---------------------------------------------------------#
#	0. Set up files for input and output
#---------------------------------------------------------#

# organize files like this or change the paths here for input
language = "english"
infolder = '../data/' + language + '/'
size = 50 #french 153 10 english 14 46
infilename = infolder + "english-brown.txt"  # corpus, instead of .dx1 file

# if an argument is specified, uses that instead of the above path for input
if len(sys.argv) > 1:
	print(sys.argv[1])
	infilename = sys.argv[1] 
if not os.path.isfile(infilename):
	print("Warning: ", infilename, " does not exist.")
if g_encoding == "utf8":
	infile = codecs.open(infilename, encoding = 'utf-8')
else:
	infile = open(infilename) 

print("\nData file: ", infilename)

# organize files like this or change the paths here for output
outfolder = '../data/'+ language + '/gibbs_wordbreaking/'
outfilename_gibbspieces = outfolder +  "gibbs_pieces.txt"
outfilename_bigrams     = outfolder +  "bigrams.txt"
outfilename_corpuslines = outfolder +  "corpus_lines.txt"
outfilename_stats   = outfolder + "stats.txt"
outfilename_lrparse = outfolder + "left_right_parse.txt"

if g_encoding == "utf8":
	outfile_gibbspieces = codecs.open(outfilename_gibbspieces, encoding =  "utf-8", mode = 'w',)
	outfile_bigrams     = codecs.open(outfilename_bigrams,     encoding =  "utf-8", mode = 'w',)
	outfile_corpuslines = codecs.open(outfilename_corpuslines, encoding =  "utf-8", mode = 'w',)
	outfile_stats   = codecs.open(outfilename_stats,   encoding =  "utf-8", mode = 'w',)
	#outfile_lrparse = codecs.open(outfilename_lrparse, encoding =  "utf-8", mode = 'w',)
	print("yes utf8")
else:
	outfile_gibbspieces = open(outfilename_gibbspieces, mode='w') 
	outfile_bigrams     = open(outfilename_bigrams,     mode='w') 
	outfile_corpuslines = open(outfilename_corpuslines, mode='w') 
	outfile_stats   = open(outfilename_stats,   mode='w') 
	#outfile_lrparse = open(outfilename_lrparse, mode='w')

	# 2016_02_25
	outfilename_addedandtrue   = outfolder + "addedandtrue.txt"
	outfilename_deletedandtrue = outfolder + "deletedandtrue.txt"
	outfile_addedandtrue   = open(outfilename_addedandtrue, mode='w')
	outfile_deletedandtrue = open(outfilename_deletedandtrue, mode='w')
	
	outfilename_biplogs = outfolder + "biplogs.txt"
	outfile_biplogs = open(outfilename_biplogs, mode='w')
	
if ResumeLoopno > 0:	
#---------------------------------------------------------#
#	Load state to resume processing	
#---------------------------------------------------------#
	print()
	print("State will be loaded from the following file:") 
	os.system("ls -l jsonpickle_infile.txt")
	print()
	this_document = load_state_from_file("jsonpickle_infile.txt")		# ln -s  <relative_or_absolute_filename>  jsonpickle_infile.txt
	random.setstate(this_document.random_state)							# restores state of random number generator
 	
else:
#---------------------------------------------------------#
#	1. Input
#---------------------------------------------------------#
	# Once jsonpickle is set up,
	# loading from a saved state (to resume processing)
	# will be an alternative to sections 1 and 2.

	this_document = Document()	
	random.seed(a=5)    # audrey  2015_12_09  #Note that integer seed is not affected by seed change in python3


	# THIS PART IS FOR CORPUS INPUT
	truelines_list = infile.readlines()
	infile.close()
	for trueline in truelines_list:
		line_object = Line("dummy")
		this_document.load_truth_and_data(trueline, line_object)

	print("Data file has", len(this_document.line_object_list), "lines,",  \
	       len(this_document.true_segment_dictionary), "distinct words,",  \
	       this_document.true_totalsegmentcount, "word occurrences.")
	print()
	

	# THIS PART IS FOR READING FROM dx1 FILE	[not yet reworked for new class structure  2016_01_21]
	#filelines= infile.readlines()
	#WordCounts={}

	## add counts for all words in dictionary
	#for line in filelines:
	#	pieces = line.split(' ')
	#	word=pieces[0] # the first column in the dx1 file is the actual word 
	#	word = ''.join([c.lower() for c in word if c not in "()1234567890"])
	#	if word in WordCounts:
	#		WordCounts[word] += 1
	#	else:
	#		WordCounts[word]= 1

	#print "We read", len(WordCounts), "words." 
	# #saves words also in list format, then sorts alphabetically (in case they're not already?)
	#wordlist = WordCounts.keys()
	#wordlist.sort()


#---------------------------------------------------------#
#	2. Random splitting of words
#---------------------------------------------------------# 

	this_document.initial_segmentation()
	print("Initial randomization completed.")
	
	loopno = -1
	this_document.precision_recall()
	this_document.output_stats(outfile_stats, loopno, show_cost = False)	

	# THIS PART IS PROBABLY TEMPORARY OR IF NOT MAY BE REORGANIZED  
	#-----------------------------#
	#       output results 		  #	
	#-----------------------------#
	#if loopno == 0  or  loopno == 10 or loopno == 20 or  loopno == 100 or loopno == NumberOfIterations -1:
	
	if False:
		if ((loopno+1) % REBASE_PERIOD == 0) or (loopno == NumberOfIterations -1): 
			for line in this_document.line_object_list: 
 				# computes cost for entire line using information recorded in line and segment objects; does not change parse.
				for piece in line.pieces:
					assert(piece in this_document.segment_object_dictionary)			# there should be no "new" pieces
				this_document.compute_bg_brokenline_cost(line)							# needed only for display on lrparse.txt, not for processing  		

		if ((loopno+1) % REBASE_PERIOD == 0):
			this_document.rebase_bg(outfile_lrparse)		# reparse, recount, recompute	
			this_document.precision_recall()
			this_document.output_stats(outfile_stats, loopno, show_cost = True)
	
		if loopno == NumberOfIterations -1:
			#this_document.output_corpuslines_detail(outfile1, loopno)									# displays text and also total line cost, detailed by segment and cost component
			this_document.output_corpuslines_textonly(outfile_corpuslines, loopno)						# "textonly" makes it easier to see diffs during development
			this_document.output_gibbspieces(outfile_gibbspieces, loopno)
			this_document.output_bigrams(outfile_bigrams, loopno)
		
			if SaveState == True:
				this_document.random_state = random.getstate()							# saves state of random number generator
				save_state_to_file(loopno, outfolder + "jsonpickle_" + str(loopno) + ".txt", this_document)
			



#----------------------------------------------------------#
#	3. Main loop
#----------------------------------------------------------#
# Markov chain based on sampling individual components (i.e., distribution of individual segment conditioned on the other segments)

for loopno in range (ResumeLoopno, NumberOfIterations):
	this_document.split_count  = 0
	this_document.merge_count = 0
	this_document.split_1newsegment_count  = 0
	this_document.split_2newsegments_count = 0
	this_document.merge_newsegment_count  = 0
	# 2016_02_25
	this_document.addedandtrue_devcount = 0
	this_document.deletedandtrue_devcount = 0

	for line in this_document.line_object_list:
		#if loopno == 86:
			#print(line.unbroken_text[0:15])
		this_document.compare_alt_parse(line)

	this_document.precision_recall()
	this_document.output_stats(outfile_stats, loopno, show_cost = False)
			                          
	
	#-----------------------------#
	#       output results 		  #	
	#-----------------------------#
	#if loopno == 0  or  loopno == 10 or loopno == 20 or  loopno == 100 or loopno == NumberOfIterations -1:
	
	if ((loopno+1) % REBASE_PERIOD == 0) or (loopno == NumberOfIterations -1): 
		for line in this_document.line_object_list: 
 			# computes cost for entire line using information recorded in line and segment objects; does not change parse.
			for piece in line.pieces:
				assert(piece in this_document.segment_object_dictionary)			# there should be no "new" pieces
			this_document.compute_bg_brokenline_cost(line)							# at this loopno, needed only for display on lrparse.txt, not for processing  		

	if ((loopno+1) % REBASE_PERIOD == 0):
		outfile_lrparse = open(outfilename_lrparse, mode='w')		
		this_document.rebase_bg(outfile_lrparse)		# reparse, recount, recompute	
		this_document.precision_recall()
		this_document.output_stats(outfile_stats, loopno, show_cost = True)
		outfile_lrparse.close()
	
	if loopno == NumberOfIterations -1:
		#this_document.output_corpuslines_detail(outfile1, loopno)									# displays text and also total line cost, detailed by segment and cost component
		this_document.output_corpuslines_textonly(outfile_corpuslines, loopno)						# "textonly" makes it easier to see diffs during development
		this_document.output_gibbspieces(outfile_gibbspieces, loopno)
		this_document.output_bigrams(outfile_bigrams, loopno)
		
		# 2016_02_25
		#this_document.output_addedandtrue(outfile_addedandtrue, loopno)
		#this_document.output_deletedandtrue(outfile_deletedandtrue, loopno)
		
		if SaveState == True:
			this_document.random_state = random.getstate()							# saves state of random number generator
			save_state_to_file(loopno, outfolder + "jsonpickle_" + str(loopno) + ".txt", this_document)
			
			

# CLOSE OUTPUT FILES SO THAT INFORMATION DERIVED BY PROGRAM CAN BE VIEWED DURING INTERACTIVE QUERIES

outfile_addedandtrue.close()
outfile_deletedandtrue.close()
#outfile_lrparse.close()
outfile_stats.close()
outfile_corpuslines.close()
outfile_gibbspieces.close()
outfile_bigrams.close()


while (True):
	command = input("Enter word:")
	if len(command)==0:
		print("enter a word.")
		continue
	if command =="exit"  :
		break

	this_document.test_unbroken_text(command)

