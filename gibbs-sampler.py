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
g_encoding = "asci"  # "utf8"


# PARAMETERS   # probably want shorter segments initially (so BREAKPROB higher than 0.1)
BitsPerLetter = 5
BREAKPROB     = 0.3		# 0.5  #0.4 #0.3  #0.2    # 0.1   # where does this probability come from? is it a statistic about languages in general/English?
DEFAULTCOUNT  = 1		# 0.5  # Used in divide_charges_among_instances() and in get_plog()
PLOGCOEFF     = 3		# used in get_plog_charge()
PENALTYFACTOR = 1.5		# extra factor in get_plog_charge() for "new" segment (not in dictionary)	1.5  2.0  1.25
REBASE_PERIOD = 10		# number of iterations between calls to rebase()
FLOAT_INF = float("inf")


NumberOfIterations = 500          # 160	 # 200	 # 400	
ResumeLoopno = 350									# Note - may want to (set a flag and) give a file to load, then get the ResumeLoop from the file 
print("\nNumber of iterations =", NumberOfIterations)
if ResumeLoopno > 0:
	print("Resume processing starting at loopno =", ResumeLoopno)

SaveState = True	# True


## ---------------------------------------------------------------------------------------##
class Segment:   # think   <morpheme> for morphology,  <word-type> or dictionary entry for wordbreaking
## ---------------------------------------------------------------------------------------##
	def __init__(self, segment_text):
		self.segment_text          = segment_text
		self.count                 = 0 
		self.phonocost             = len(segment_text) * float(BitsPerLetter)
		self.ordercost             = math.log (math.factorial(len(segment_text)), 2)
		self.inclusioncost         = 1.0
		self.phonocost_portion     = 0.0		# phonocost / count
		self.ordercost_portion     = 0.0		# etc.
		self.inclusioncost_portion = 0.0
		self.sum_dictcosts_portion = 0.0 		# (phonocost + ordercost + inclusioncost) / count

		self.plog                  = 0.0		# CAUTION: plog depends on total_pieces_count.
												# self.plog is not updated except when this segment is involved in a parsing decision.
												# Use self.get_plog(totalsegmentcount) for correct value.
												# SEE ALSO document.fetch_plogged_segment_from_dictionary
												
												
												
	def divide_charges_among_instances(self): 
		if self.count != 0:
			divisor = self.count
		else:
			divisor = DEFAULTCOUNT
		self.phonocost_portion     = self.phonocost/divisor		# Note that phonocost is float; also '/' is true division in python3
		self.ordercost_portion     = self.ordercost/divisor
		self.inclusioncost_portion = self.inclusioncost/divisor
		self.sum_dictcosts_portion = self.phonocost_portion + self.ordercost_portion + self.inclusioncost_portion


	def get_plog(self, totalsegmentcount):
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
		
	def get_instance_cost(self, totalsegmentcount):
		return self.get_plog_charge(totalsegmentcount) + self.sum_dictcosts_portion
		

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
		self.segment_object_dictionary	= {}			# dictionary  key: piece   value: segment object
		self.totalsegmentcount   		= 0
		self.merger_count         		= 0
		self.split_count          		= 0
		self.merger_newsegment_count	= 0				# these 3 added on Feb. 2, 2016
		self.split_1newsegment_count	= 0
		self.split_2newsegments_count	= 0
		self.split_merger_history 		= []
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
		self.other_statistics     		= 0.0			# What should be measured?
		self.random_state				= None			# save state of random number generator in this spot
														# so that it will be preserved by pickling
		self.true_segment_dictionary	= {}
		self.true_totalsegmentcount		= 0
		
		

	def output_corpuslines_detail(self, outfile):
		for line in self.line_object_list:
			self.populate_line_displaylists(line)
			line.display_detail(outfile)			# displays text followed by line cost, detailed by segment and component

	def output_corpuslines_textonly(self, outfile):
		for line in self.line_object_list:
			line.displaytextonly(outfile)	# displays only unbroken line and its parse
			print("       cost: %7.3f\n" % line.total_cost, end=' ', file=outfile)	
	
	def output_gibbspieces(self, outfile):
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
		for n in range(len(countslist)):
			print(n, countslist[n][0], countslist[n][1], file=outfile)
		
	def output_addedandtrue(self, outfile):
		#countslist = sorted(reduced_dictionary.items(), key = lambda x:(x[1],x[0]), reverse=True)	#primary sort key is count, secondary is alphabetical
		countslist = sorted(self.addedandtrue_dictionary.items(), key = lambda x:x[0])				#secondary sort is alphabetical (ascending)
		countslist = sorted(countslist, key = lambda x:x[1], reverse=True)							#primary sort is by count (descending)

		print("\n=== addedandtrue_dictionary ===", file=outfile)
		for n in range(len(countslist)):
			print(n, countslist[n][0], countslist[n][1], file=outfile)
		
	def output_deletedandtrue(self, outfile):
		#countslist = sorted(reduced_dictionary.items(), key = lambda x:(x[1],x[0]), reverse=True)	#primary sort key is count, secondary is alphabetical
		countslist = sorted(self.deletedandtrue_dictionary.items(), key = lambda x:x[0])					#secondary sort is alphabetical (ascending)
		countslist = sorted(countslist, key = lambda x:x[1], reverse=True)							#primary sort is by count (descending)

		print("\n=== deletedandtrue_dictionary ===", file=outfile)
		for n in range(len(countslist)):
			print(n, countslist[n][0], countslist[n][1], file=outfile)
		
	
	def fetch_plogged_segment_from_dictionary(self, piece):  
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

		
	
	def initial_segmentation(self):
		dictionary = self.segment_object_dictionary
		for ln in self.line_object_list:
			start = 0		 
			ln.breaks.append(0)								# always put a break at the beginning
			for n in range(1, len(ln.unbroken_text)):		# won't randomly put a break at the beginning or end
				if random.random() < BREAKPROB:				# about every 10 (= 1/BREAKPROB) letters add a break
					piece = ln.unbroken_text[start:n]
					ln.pieces.append(piece)
					ln.breaks.append( n )
					start = n	
					self.totalsegmentcount += 1				# ALERT - for any item in or about to go into the dictionary,
					if not piece in dictionary:				# increment totalsegmentcount BEFORE populating its plog variable		  
						dictionary[piece] = self.new_segment_object(piece, 1)
					else:
						dictionary[piece].count += 1
					
			if start < len(ln.unbroken_text):      # should always be true...
				piece = ln.unbroken_text[start:]
				ln.pieces.append(piece)
				ln.breaks.append( len(ln.unbroken_text) )   # always put a break at the end
				self.totalsegmentcount += 1
				if not piece in dictionary:
					dictionary[piece] = self.new_segment_object(piece, 1)
				else:
					dictionary[piece].count += 1


		# Now that forming of segments is complete, 
		# fill in the information that depends on their count.	 
		for sgmt in self.segment_object_dictionary.values():
			sgmt.divide_charges_among_instances()
			sgmt.get_plog(self.totalsegmentcount)
	


	def compare_alt_parse(self, line, outfile_del_analysis):
#	def compare_alt_parse(self, line):
		# EXPLANATORY NOTE
		###		point = 1 + int(random.random() * (len(line.unbroken_text)-1)) 
		# Before python3, this line and the first line of code below were equivalent.
		# randrange changed in python3, so now program output doesn't match pre-python3 runs.
		# Using random.random() as shown above DOES exactly reproduce pre-python3 results,
		# except for spacing and ordering.
	
		point = random.randrange( 1, len(line.unbroken_text))	# selects a point to consider splitting at, not beginning or end
																# Suppose len(line.unbroken_text) = 100
																# Index runs from 0 through 99. Don't pick 0. 
																# But OK to pick 99. That splits off the last character of the line.
		breakpoint, breakindex = line.break_cover(point)

	
		# Splitting:
		if point < breakpoint:												# point may be any character within its piece except the first
		
			leftbreak  = line.breaks[breakindex-1]
			rightbreak = line.breaks[breakindex]       						# Note rightbreak == breakpoint

			# local contribution to line cost as presently configured
			singlepiece = line.unbroken_text[leftbreak:rightbreak]			# Note singlepiece == line.pieces[breakindex-1]
			if singlepiece not in self.segment_object_dictionary:
				print("Error in CompareAltParse: singlepiece (=", singlepiece, ") not found in dictionary at line ='", line.unbroken_text, "'.")
				sys.exit()
			singlesegment = self.fetch_plogged_segment_from_dictionary(singlepiece)
			current_contribution = singlesegment.get_instance_cost(self.totalsegmentcount)

			
			# alternative contribution 	
			leftpiece  = line.unbroken_text[leftbreak:point]
			rightpiece = line.unbroken_text[point:rightbreak]
			
			if leftpiece in self.segment_object_dictionary:
				left_segment  = self.fetch_plogged_segment_from_dictionary(leftpiece)
			else:
				left_segment  = self.new_segment_object(leftpiece, 0)
			
			if rightpiece in self.segment_object_dictionary:
				right_segment  = self.fetch_plogged_segment_from_dictionary(rightpiece)
			else:
				right_segment  = self.new_segment_object(rightpiece, 0)
			
			alt_contribution = left_segment.get_instance_cost(self.totalsegmentcount)   +  \
							   right_segment.get_instance_cost(self.totalsegmentcount)  +  \
			                   math.log(1 + len(line.pieces), 2)
			# last addend is adjustment to present value of log(factorial( len(self.pieces) ))

			
			# FOR SAMPLING, USE THESE LINES
			selection = random.random()		# selects uniformly from [0.0,1.0)
			normalized_alt_contribution = alt_contribution / (alt_contribution + current_contribution)
			if normalized_alt_contribution < selection:
			
			# FOR DETERMINISTIC SELECTION, USE THIS LINE
			#if alt_contribution < current_contribution:
				# UPDATE THE PARSE
				line.piecesorder_cost += math.log(1 + len(line.pieces), 2)
				line.pieces[breakindex-1] = leftpiece		# i.e., replace singlepiece by leftpiece
				line.breaks.insert(breakindex, point)		# or use addcut  
				line.pieces.insert(breakindex, rightpiece)
				 
				# UPDATE GLOBAL COUNTS
				if left_segment.count == 0 and right_segment.count == 0:
					self.split_2newsegments_count += 1
				elif left_segment.count == 0 or right_segment.count == 0:
					self.split_1newsegment_count += 1
				self.split_count += 1
				self.totalsegmentcount += 1
				
				# UPDATE DICTIONARY ENTRIES
				singlesegment.count -= 1
				if singlesegment.count == 0:
					del self.segment_object_dictionary[singlepiece]
					# 2016_02_25
					if singlepiece in self.true_segment_dictionary:		# additional info; no contribution to processing
						self.deletedandtrue_devcount += 1
						self.deletedandtrue_dictionary[singlepiece] = self.true_segment_dictionary[singlepiece]
						print("Split", file=outfile_del_analysis)
						print("   Pieces:        single =", singlepiece, "   left =", leftpiece, "   right =", rightpiece, file=outfile_del_analysis)
						print("   Cost_contribs: current =", current_contribution, "   alt =", alt_contribution, file=outfile_del_analysis)
						print("   Counts:        single =", singlesegment.count, "   left =", left_segment.count, "   right =", right_segment.count, file=outfile_del_analysis)
						print("   True count:    single =", self.true_segment_dictionary[singlepiece], file=outfile_del_analysis)
				else:
					singlesegment.divide_charges_among_instances()
					singlesegment.plog = singlesegment.get_plog(self.totalsegmentcount)
				
				if leftpiece not in self.segment_object_dictionary:
					self.segment_object_dictionary[leftpiece] = left_segment
					# 2016_02_25
					if leftpiece in self.true_segment_dictionary:		# additional info; no contribution to processing
						self.addedandtrue_devcount += 1
						self.addedandtrue_dictionary[leftpiece] = self.true_segment_dictionary[leftpiece]
				# REORDERED    2016_03_05
				self.segment_object_dictionary[leftpiece].count += 1
				self.segment_object_dictionary[leftpiece].divide_charges_among_instances()
				self.segment_object_dictionary[leftpiece].plog = self.segment_object_dictionary[leftpiece].get_plog(self.totalsegmentcount)
				
				if rightpiece not in self.segment_object_dictionary:
					self.segment_object_dictionary[rightpiece] = right_segment
					# 2016_02_25
					if rightpiece in self.true_segment_dictionary:		# additional info; no contribution to processing
						self.addedandtrue_devcount += 1
						self.addedandtrue_dictionary[rightpiece] = self.true_segment_dictionary[rightpiece]
				# REORDERED TO CORRECT ERROR WITH "-m-m" SPLIT TO NEW SEGMENTS "-m -m" MISCOUNT   2016_03_05
				self.segment_object_dictionary[rightpiece].count += 1
				self.segment_object_dictionary[rightpiece].divide_charges_among_instances()
				self.segment_object_dictionary[rightpiece].plog = self.segment_object_dictionary[rightpiece].get_plog(self.totalsegmentcount)


		
		# Merging:
		elif point == line.breaks[breakindex]:								# here point is the first character within its piece

			leftbreak  = line.breaks[breakindex-1]
			rightbreak = line.breaks[breakindex+1]

			# local contribution as presently configured
			leftpiece  = line.unbroken_text[leftbreak:point]				# leftpiece  == line.pieces[breakindex-1]
			rightpiece = line.unbroken_text[point:rightbreak]				# rightpiece == line.pieces[breakindex]
			
			if leftpiece not in self.segment_object_dictionary:
				print("Error in CompareAltParse: leftpiece (= ", leftpiece, ") not found in dictionary at line = '", line.unbroken_text, "'.")
				sys.exit()
			if rightpiece not in self.segment_object_dictionary:
				print("Error in CompareAltParse: rightpiece (= ", rightpiece, ") not found in dictionary at line = '", line.unbroken_text, "'.")
				sys.exit()
			left_segment  = self.fetch_plogged_segment_from_dictionary(leftpiece)
			right_segment = self.fetch_plogged_segment_from_dictionary(rightpiece)
			current_contribution  = left_segment.get_instance_cost(self.totalsegmentcount) + right_segment.get_instance_cost(self.totalsegmentcount)

			# alternative contribution 	
			merged_piece = line.unbroken_text[leftbreak:rightbreak]
			if merged_piece in self.segment_object_dictionary:
				merged_segment = self.fetch_plogged_segment_from_dictionary(merged_piece)
			else:
				merged_segment = self.new_segment_object(merged_piece, 0)
						
			alt_contribution = merged_segment.get_instance_cost(self.totalsegmentcount) - math.log(len(line.pieces), 2)
			# last addend is adjustment to present value of log(factorial( len(self.pieces) ))

			
			# FOR SAMPLING, USE THESE LINES
			selection = random.random()		# selects uniformly from [0.0,1.0)
			normalized_alt_contribution = alt_contribution / (alt_contribution + current_contribution)
			if normalized_alt_contribution < selection:
			
			# FOR DETERMINISTIC SELECTION, USE THIS LINE
			#if alt_contribution < current_contribution:
				# UPDATE THE PARSE
				line.piecesorder_cost -= math.log(len(line.pieces), 2)
				line.pieces[breakindex-1] = merged_piece				# i.e., replace leftpiece by merged_piece
				line.pieces.pop(breakindex)
				line.breaks.pop(breakindex)
				
				# UPDATE GLOBAL COUNTS
				if merged_segment.count == 0:
					self.merger_newsegment_count += 1
				self.merger_count += 1
				self.totalsegmentcount -= 1
				
				# UPDATE DICTIONARY ENTRIES
				if merged_piece not in self.segment_object_dictionary:
					self.segment_object_dictionary[merged_piece] = merged_segment
					# 2016_02_25
					if merged_piece in self.true_segment_dictionary:		# additional info; no contribution to processing
						self.addedandtrue_devcount +=1
						self.addedandtrue_dictionary[merged_piece] = self.true_segment_dictionary[merged_piece]
				# REORDERED   2016_03_05
				self.segment_object_dictionary[merged_piece].count += 1
				self.segment_object_dictionary[merged_piece].divide_charges_among_instances()
				self.segment_object_dictionary[merged_piece].plog = self.segment_object_dictionary[merged_piece].get_plog(self.totalsegmentcount)
					
				left_segment.count -= 1
				if left_segment.count == 0:
					del self.segment_object_dictionary[leftpiece]
					# 2016_02_25
					if left_segment in self.true_segment_dictionary:		# additional info; no contribution to processing
						self.deletedandtrue_devcount += 1
						self.deletedandtrue_dictionary[left_segment] = self.true_segment_dictionary[left_segment]
						print("Merge", file=outfile_del_analysis)
						print("   Pieces:        merged =", merged_piece, "   left =", leftpiece, "   right =", rightpiece, file=outfile_del_analysis)
						print("   Cost_contribs: current =", current_contribution, "   alt =", alt_contribution, file=outfile_del_analysis)
						print("   Counts:        left =", left_segment.count, "   right =", right_segment.count, file=outfile_del_analysis)
						print("   True count:    left =", self.true_segment_dictionary[leftpiece], file=outfile_del_analysis)
				else:
					left_segment.divide_charges_among_instances()
					left_segment.plog = left_segment.get_plog(self.totalsegmentcount)
				
				right_segment.count -= 1
				if right_segment.count == 0:
					del self.segment_object_dictionary[rightpiece]
					# 2016_02_25
					if right_segment in self.true_segment_dictionary:		# additional info; no contribution to processing
						self.deletedandtrue_devcount += 1
						self.deletedandtrue_dictionary[right_segment] = self.true_segment_dictionary[right_segment]
						print("Merge", file=outfile_del_analysis)
						print("   Piecess:       merged =", mergedpiece, "   left =", leftpiece, "   right =", rightpiece, file=outfile_del_analysis)
						print("   Cost_contribs: current =", current_contribution, "   alt =", alt_contribution, file=outfile_del_analysis)
						print("   Counts:        left =",  left_segment.count, "   right =", right_segment.count, file=outfile_del_analysis)
						print("   True count:    right =", self.true_segment_dictionary[rightpiece], file=outfile_del_analysis)
				else:
					right_segment.divide_charges_among_instances()
					right_segment.plog = right_segment.get_plog(self.totalsegmentcount)
				


	def lrparse_line(self, line, longest_dictionary_entry_length, outfile  ):				# from wordbreaker.py: ParseWord()   Needs different name.  outfile is for verbose (mostly --last part always prints).
         
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


	def rebase(self, verbose_outfile):
		
		# REPARSE
		longest = 0
		for piece in self.segment_object_dictionary:
			if len(piece) > longest:
				longest = len(piece)
		print("longest_entry_length =", longest)
		print("longest_entry_length =", longest, file=verbose_outfile)
		
		print("parsing...")
		for ln in self.line_object_list:
			(parsed_line, bitcost) = self.lrparse_line(ln, longest, verbose_outfile)
			ln.pieces = list(parsed_line)		# copy
			ln.populate_breaks_from_pieces()
			#ln.total_cost = bitcost  [stored for comparison in RECOMPUTE section]
			

		# RECOUNT SEGMENTS
		# rebuild the dictionary   IS THERE ANYTHING ELSE THAT NEEDS TO BE REINITED ????
		print("updating segment counts in the dictionary...")
		newdictionary = {}
		self.totalsegmentcount = 0
				
		for ln in self.line_object_list:
			for piece in ln.pieces:
				self.totalsegmentcount += 1				# ALERT - for any item in or about to go into the dictionary,
				if not piece in newdictionary:			# increment totalsegmentcount BEFORE populating its plog variable		  
					newdictionary[piece] = self.new_segment_object(piece, 1)
				else:
					newdictionary[piece].count += 1
		
		# fill in the information that depends on the count	 
		for sgmt in newdictionary.values():
			sgmt.divide_charges_among_instances()
			sgmt.get_plog(self.totalsegmentcount)
			
		self.segment_object_dictionary = copy.deepcopy(newdictionary)	


		# RECOMPUTE
		print("computing line costs...")
		for ln in self.line_object_list:
			for piece in ln.pieces:
				assert(piece in self.segment_object_dictionary)		# there should be no "new" pieces
			self.compute_brokenline_cost(ln)

	

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



	def output_stats(self, outfile, loopno):
		if (loopno % REBASE_PERIOD == 0):
			print()
			print(file=outfile)		

		formatstring = "%4d   S:%4d   M:%4d   new:%2d %2d   %3d    At:%4d   Dt:%4d      BP: %6.4f   BR: %6.4f         TP: %6.4f   TR: %6.4f         DP: %6.4f   DR: %6.4f"

		print( formatstring % (loopno,		
				self.split_count,
				self.merger_count,  
				self.split_1newsegment_count, 
		        self.split_2newsegments_count,
		        self.merger_newsegment_count,
		        
		        self.addedandtrue_devcount,
		        self.deletedandtrue_devcount,

		        this_document.break_precision,
		        this_document.break_recall,
		        this_document.token_precision,
		        this_document.token_recall,
		        this_document.dictionary_precision,
		        this_document.dictionary_recall))

		print( formatstring % (loopno,		
				self.split_count,
				self.merger_count,  
				self.split_1newsegment_count, 
		        self.split_2newsegments_count,
		        self.merger_newsegment_count,
		        
		        self.addedandtrue_devcount,
		        self.deletedandtrue_devcount,

		        this_document.break_precision,
		        this_document.break_recall,
		        this_document.token_precision,
		        this_document.token_recall,
		        this_document.dictionary_precision,
		        this_document.dictionary_recall),
		        file=outfile)


	
	def test_unbroken_text(self, text):	
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
##		End of class Document:
## ---------------------------------------------------------------------------------------#


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
	serialstr = jsonpickle.encode(document_object)
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
	document = jsonpickle.decode(serialstr)

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
outfilename_corpuslines = outfolder +  "corpus_lines.txt"
outfilename_stats   = outfolder + "stats.txt"
outfilename_lrparse = outfolder + "left_right_parse.txt"

if g_encoding == "utf8":
	outfile_gibbspieces = codecs.open(outfilename_gibbspieces, encoding =  "utf-8", mode = 'w',)
	outfile_corpuslines = codecs.open(outfilename_corpuslines, encoding =  "utf-8", mode = 'w',)
	outfile_stats   = codecs.open(outfilename_stats,   encoding =  "utf-8", mode = 'w',)
	outfile_lrparse = codecs.open(outfilename_lrparse, encoding =  "utf-8", mode = 'w',)
	print("yes utf8")
else:
	outfile_gibbspieces = open(outfilename_gibbspieces, mode='w') 
	outfile_corpuslines = open(outfilename_corpuslines, mode='w') 
	outfile_stats   = open(outfilename_stats,   mode='w') 
	outfile_lrparse = open(outfilename_lrparse, mode='w')

	# 2016_02_25
	outfilename_addedandtrue   = outfolder + "addedandtrue.txt"
	outfilename_deletedandtrue = outfolder + "deletedandtrue.txt"
	outfile_addedandtrue   = open(outfilename_addedandtrue, mode='w')
	outfile_deletedandtrue = open(outfilename_deletedandtrue, mode='w')
	
	#2016_02_27
	outfilename_del_analysis = outfolder + "del_analysis.txt"
	outfile_del_analysis     = open(outfilename_del_analysis, mode='w')
	
	
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
	this_document.output_stats(outfile_stats, loopno)	

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
				this_document.compute_brokenline_cost(line)								# needed only for display on lrparse.txt, not for processing  		

		if ((loopno+1) % REBASE_PERIOD == 0):
			this_document.rebase(outfile_lrparse)		# reparse, recount, recompute	
			this_document.precision_recall()
			this_document.output_stats(outfile_stats, loopno)
	
		if loopno == NumberOfIterations -1:
			print("----------------------------------------\nLoop number:", loopno, file=outfile_corpuslines)
			print("----------------------------------------", file=outfile_corpuslines)
			#this_document.output_corpuslines_detail(outfile1)									# displays text and also total line cost, detailed by segment and cost component
			this_document.output_corpuslines_textonly(outfile_corpuslines)						# "textonly" makes it easier to see diffs during development

			print("----------------------------------------\nLoop number:", loopno, file=outfile_gibbspieces)
			print("----------------------------------------", file=outfile_gibbspieces)			
			this_document.output_gibbspieces(outfile_gibbspieces)
		
			if SaveState == True:
				this_document.random_state = random.getstate()							# saves state of random number generator
				save_state_to_file(loopno, outfolder + "jsonpickle_" + str(loopno) + ".txt", this_document)
			



#----------------------------------------------------------#
#	3. Main loop
#----------------------------------------------------------#
# Markov chain based on sampling individual components (i.e., distribution of individual segment conditioned on the other segments)

for loopno in range (ResumeLoopno, NumberOfIterations):
	this_document.split_count  = 0
	this_document.merger_count = 0
	this_document.split_1newsegment_count  = 0
	this_document.split_2newsegments_count = 0
	this_document.merger_newsegment_count  = 0
	# 2016_02_25
	this_document.addedandtrue_devcount = 0
	this_document.deletedandtrue_devcount = 0

	for line in this_document.line_object_list:
		this_document.compare_alt_parse(line, outfile_del_analysis)

	this_document.precision_recall()
	this_document.output_stats(outfile_stats, loopno)
			                          
	
	#-----------------------------#
	#       output results 		  #	
	#-----------------------------#
	#if loopno == 0  or  loopno == 10 or loopno == 20 or  loopno == 100 or loopno == NumberOfIterations -1:
	
	if ((loopno+1) % REBASE_PERIOD == 0) or (loopno == NumberOfIterations -1): 
		for line in this_document.line_object_list: 
 			# computes cost for entire line using information recorded in line and segment objects; does not change parse.
			for piece in line.pieces:
				assert(piece in this_document.segment_object_dictionary)			# there should be no "new" pieces
			this_document.compute_brokenline_cost(line)								# needed only for display on lrparse.txt, not for processing  		

	if ((loopno+1) % REBASE_PERIOD == 0):
		this_document.rebase(outfile_lrparse)		# reparse, recount, recompute	
		this_document.precision_recall()
		this_document.output_stats(outfile_stats, loopno)
	
	if loopno == NumberOfIterations -1:
		print("----------------------------------------\nLoop number:", loopno, file=outfile_corpuslines)
		print("----------------------------------------", file=outfile_corpuslines)
		#this_document.output_corpuslines_detail(outfile1)									# displays text and also total line cost, detailed by segment and cost component
		this_document.output_corpuslines_textonly(outfile_corpuslines)						# "textonly" makes it easier to see diffs during development

		print("----------------------------------------\nLoop number:", loopno, file=outfile_gibbspieces)
		print("----------------------------------------", file=outfile_gibbspieces)			
		this_document.output_gibbspieces(outfile_gibbspieces)
		
		# 2016_02_25
		
		print("----------------------------------------\nLoop number:", loopno, file=outfile_gibbspieces)
		print("----------------------------------------", file=outfile_gibbspieces)			
		this_document.output_addedandtrue(outfile_addedandtrue)
		
		print("----------------------------------------\nLoop number:", loopno, file=outfile_gibbspieces)
		print("----------------------------------------", file=outfile_gibbspieces)			
		this_document.output_deletedandtrue(outfile_deletedandtrue)
		
		if SaveState == True:
			this_document.random_state = random.getstate()							# saves state of random number generator
			save_state_to_file(loopno, outfolder + "jsonpickle_" + str(loopno) + ".txt", this_document)
			
			

# CLOSE OUTPUT FILES SO THAT INFORMATION DERIVED BY PROGRAM CAN BE VIEWED DURING INTERACTIVE QUERIES

outfile_del_analysis.close()
outfile_addedandtrue.close()
outfile_deletedandtrue.close()
outfile_lrparse.close()
outfile_stats.close()
outfile_corpuslines.close()
outfile_gibbspieces.close()


while (True):
	command = input("Enter word:")
	if len(command)==0:
		print("enter a word.")
		continue
	if command =="exit"  :
		break

	this_document.test_unbroken_text(command)

