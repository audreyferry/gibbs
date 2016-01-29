#!/usr/bin/env python3

import sys
import os
import random
import math
g_encoding = "asci"  # "utf8"
shift_counter = []

random.seed(a=5)    # audrey  2015_12_09  #Note that integer seed is not affected by seed change in python3

# PARAMETERS   # probably want shorter segments initially (so BREAKPROB higher than 0.1)
BitsPerLetter = 5
BREAKPROB     = 0.1		# 0.5  #0.4 #0.3  #0.2    # 0.1   # where does this probability come from? is it a statistic about languages in general/English?
DEFAULTCOUNT  = 1		# 0.5  # Used in GetCount()   tbd  2016_01_09
PLOGCOEFF     = 10		# used in both GetSegmentCost() and EvaluateWordCost()
						# expect redesign in future


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

				
	def get_plog_charge(self, totalsegmentcount):
		return PLOGCOEFF * self.get_plog(totalsegmentcount)

		
	def get_instance_cost(self, totalsegmentcount):
		return self.get_plog_charge(totalsegmentcount) + self.sum_dictcosts_portion
		

## ---------------------------------------------------------------------------------------##
class Line:     # a bounded expression  <word in dx1 file>    <line in corpus>
## ---------------------------------------------------------------------------------------##
	def __init__(self, unbroken_text):
		self.unbroken_text              = unbroken_text	# (former self.word)
		self.true_text                  = []		# depends whether we derive unbroken from true or just read unbroken directly
		self.breaks                     = []
		self.pieces                     = []		# list of strings  <morphs>   <words>   NOT segment objects 

		self.piecesorder_cost			= 0.0
		self.total_cost 		        = 0.0		# Since only local information is needed for parsing decisions,
														# total_cost for the line and the lists below are not maintained at intermediate stages.
														# Use the document function compute_parsedline_cost() (former EvaluateWordParse)
														# to obtain (and if desired display) line cost information.

		self.phonocost_portion_list 	= []		# List per segment of phonocost_portion, in proper order. Similarly for other list variables.
		self.ordercost_portion_list     = []		# The lists are used to arrange segment information attractively for display.
		self.inclusioncost_portion_list = []		# Are they useful to retain? Should they be in a separate Display class?
		self.plog_list 		            = []
		self.subtotal_list              = []		# list per segment of following quantity: 
													# ordercost_portion + phonocost_portion + inclusioncost_portion + plog
		
				

	def getpiece(self, pieceno):
		return self.unbroken_text[self.breaks[pieceno-1]:self.breaks[pieceno]]		# note that getpiece(k) returns pieces[k-1]
																					# for example, getpiece(1) returns pieces[0]
																					

	def displaytextonly(self, outfile):
		FormatString1 = "%20s"
		print(self.unbroken_text, " breaks:",  self.breaks, file=outfile)
		print("  pieces:", end=' ', file=outfile)				# FIX SPACING?	 
		for n in range(1,len(self.breaks)):
			print(self.getpiece(n), "", end=' ', file=outfile)	# note the comma for continuation
		print(file=outfile)
	

	def display(self, outfile):
		FormatString1 = "%20s"
		FormatString2 = "%8.1f"
		FormatString3 = "%8s"

		print("\n", self.unbroken_text, "breaks:",  self.breaks, file=outfile)		
		print(FormatString1 %("pieces:"), end=' ', file=outfile)   # FIX SPACING?		 
		for n in range(1,len(self.breaks)):
			print(FormatString3 %(self.getpiece(n)), end=' ', file=outfile)
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


	def displaytoscreen(self):
		FormatString1 = "%20s"
		FormatString2 = "%8.1f"
		FormatString3 = "%8s"		 

		print(self.unbroken_text, "breaks", self.breaks)
		
		print(FormatString1 %("pieces:"), end=' ')		 
		for n in range(1,len(self.breaks)):
			print(FormatString3 %(self.getpiece(n)), end=' ')
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
		print(FormatString1 %("log (num_pieces!)!:"), end=' ')
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
		self.split_count          		= 0
		self.merger_count         		= 0
		self.split_merger_history 		= []
		self.other_statistics     		= 0.0			# What should be measured?



	def print_parsed_lines(self, outfile):
		for line in self.line_object_list:
			line.display(outfile)			# displays text along with total line cost, detailed by segment and component

	def print_parsed_lines_textonly(self, outfile):
		for line in self.line_object_list:
			line.displaytextonly(outfile)	# displays only unbroken line and its parse
	
	
	def print_segment_counts(self, outfile):
		# Additional information is stored in the segment_object_dictionary,
		# but only count will be displayed on the outfile.
		
		reduced_dictionary = {}
		for this_piece, this_segment in self.segment_object_dictionary.items():
			reduced_dictionary[this_piece] = this_segment.count
		countslist = sorted(reduced_dictionary.items(), key = lambda x:x[1], reverse=True)
		
		print("Dictionary:\n", file=outfile)
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
	


	def compare_alt_parse(self, line):
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
				print("Error in CompareAltParse: singlepiece (= ", singlepiece, ") not found in dictionary at line = '", line.unbroken_text, "'.")
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


			if alt_contribution < current_contribution:
				# UPDATE THE PARSE
				line.piecesorder_cost += math.log(1 + len(line.pieces), 2)
				line.pieces[breakindex-1] = leftpiece		# i.e., replace singlepiece by leftpiece
				line.breaks.insert(breakindex, point)		# or use addcut  
				line.pieces.insert(breakindex, rightpiece)
				 
				# UPDATE GLOBAL COUNTS
				self.split_count += 1
				self.totalsegmentcount += 1
				
				# UPDATE DICTIONARY ENTRIES
				singlesegment.count -= 1
				if singlesegment.count == 0:
					del self.segment_object_dictionary[singlepiece]
				else:
					singlesegment.divide_charges_among_instances()
					singlesegment.plog = singlesegment.get_plog(self.totalsegmentcount)
				
				left_segment.count += 1
				left_segment.divide_charges_among_instances()
				left_segment.plog = left_segment.get_plog(self.totalsegmentcount)
				if leftpiece not in self.segment_object_dictionary:
					self.segment_object_dictionary[leftpiece] = left_segment
				
				right_segment.count += 1
				right_segment.divide_charges_among_instances()
				right_segment.plog = right_segment.get_plog(self.totalsegmentcount)
				if rightpiece not in self.segment_object_dictionary:
					self.segment_object_dictionary[rightpiece] = right_segment


		
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


			if alt_contribution < current_contribution:
				# UPDATE THE PARSE
				line.piecesorder_cost -= math.log(len(line.pieces), 2)
				line.pieces[breakindex-1] = merged_piece				# i.e., replace leftpiece by merged_piece
				line.pieces.pop(breakindex)
				line.breaks.pop(breakindex)
				
				# UPDATE GLOBAL COUNTS
				self.merger_count += 1
				self.totalsegmentcount -= 1
				
				# UPDATE DICTIONARY ENTRIES
				merged_segment.count += 1
				merged_segment.divide_charges_among_instances()
				merged_segment.plog = merged_segment.get_plog(self.totalsegmentcount)
				if merged_piece not in self.segment_object_dictionary:
					self.segment_object_dictionary[merged_piece] = merged_segment
					
				left_segment.count -= 1
				if left_segment.count == 0:
					del self.segment_object_dictionary[leftpiece]
				else:
					left_segment.divide_charges_among_instances()
					left_segment.plog = left_segment.get_plog(self.totalsegmentcount)
				
				right_segment.count -= 1
				if right_segment.count == 0:
					del self.segment_object_dictionary[rightpiece]
				else:
					right_segment.divide_charges_among_instances()
					right_segment.plog = right_segment.get_plog(self.totalsegmentcount)
				


	def compute_parsedline_cost(self, line):	
		line.total_cost = 0.0							# should already be set by __init__
		for piece in line.pieces:
			if piece in self.segment_object_dictionary:
				this_segment = self.fetch_plogged_segment_from_dictionary(piece)
			else:
				this_segment = self.new_segment_object(piece, 0)
				
			piece_cost = this_segment.get_instance_cost(self.totalsegmentcount)
			line.total_cost += piece_cost
		
			# THESE LIST VARIABLES EXIST FOR DISPLAY ONLY  [expect changes if class structure is reworked]
			line.plog_list.append(this_segment.get_plog_charge(self.totalsegmentcount))  #(PLOGCOEFF * this_instance.plog)
			line.phonocost_portion_list.append(this_segment.phonocost_portion)	
			line.ordercost_portion_list.append(this_segment.ordercost_portion)	
			line.inclusioncost_portion_list.append(this_segment.inclusioncost_portion)
			line.subtotal_list.append(piece_cost) 		


		line.piecesorder_cost =  math.log (math.factorial(len(line.pieces)), 2)
		line.total_cost += line.piecesorder_cost
		return  


	def test_unbroken_text(self, text):	
		print("\npoint = 0 (i.e., unbroken text)")		
		test_parse = Line(text)
		test_parse.breaks = [0, len(text)]
		test_parse.pieces.append(text)

		self.compute_parsedline_cost(test_parse)
		bestscore = test_parse.total_cost
		bestlocation = 0
		test_parse.displaytoscreen()
	
		for point in range(1, len(text)):
			print("\npoint =", point)
			test_parse = Line(text)
			test_parse.breaks = [0, point, len(text)]
			test_parse.pieces.append(text[0:point])
			test_parse.pieces.append(text[point:])

			self.compute_parsedline_cost(test_parse)
			if test_parse.total_cost < bestscore:
				bestscore = test_parse.total_cost
				bestlocation = point
			test_parse.displaytoscreen()

		print("\nBest score = ", bestscore, "at point = ", bestlocation, "\n")    # FORMAT bestscore AS %8.1f

## ---------------------------------------------------------------------------------------##
##		End of class Document:
## ---------------------------------------------------------------------------------------#

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
#	1. Set up files for input and output
#---------------------------------------------------------#

# organize files like this or change the paths here for input
language = "english"
infolder = '../data/' + language + '/'
size = 50 #french 153 10 english 14 46
infilename = infolder + "english-brown-unbroken.txt"  # unbroken corpus, instead of .dx1 file

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

print("Data file: ", infilename)

# organize files like this or change the paths here for output
outfolder = '../data/'+ language + '/gibbs_wordbreaking/'
outfilename = outfolder +  "gibbs_pieces.txt"
outfilename1 = outfolder +  "word_list.txt"
outfilename2 = outfolder +  "split_merge_counts.txt"
if g_encoding == "utf8":
	outfile = codecs.open(outfilename, encoding =  "utf-8", mode = 'w',)
	outfile1 = codecs.open(outfilename1, encoding =  "utf-8", mode = 'w',)
	outfile2 = codecs.open(outfilename2, encoding =  "utf-8", mode = 'w',)
	print("yes utf8")
else:
	outfile = open(outfilename,mode='w') 
	outfile1 = open(outfilename1,mode='w') 
	outfile2 = open(outfilename2,mode='w') 

 
#---------------------------------------------------------#
#	2. Input
#---------------------------------------------------------#
# Once jsonpickle is set up,
# loading from a saved state (to resume processing)
# will be an alternatives to sections 2 and 3.

this_document = Document()	
# THIS PART IS FOR CORPUS INPUT
textline_list = infile.readlines()
for textline in textline_list:
	this_document.line_object_list.append(Line(textline))
print("There are ", len(this_document.line_object_list), "lines in this document")

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
#	3. Random splitting of words
#---------------------------------------------------------# 
this_document.initial_segmentation()
print("End of initial randomization.") 



#----------------------------------------------------------#
#	4. Main loop
#----------------------------------------------------------#
NumberOfIterations = 25   # 160	 # 200	 # 400	
print("Number of iterations: ", NumberOfIterations)
LoopNumberAtWhichWeStartTracking = 20

# Markov chain based on sampling individual components (i.e., distribution of individual segment conditioned on the other segments)
for loopno in range (NumberOfIterations):

	this_document.split_count = 0
	this_document.merger_count = 0
	
	for line in this_document.line_object_list:
		this_document.compare_alt_parse(line)

	#if this_document.split_count + this_document.merger_count > 0:
	if True:
		print("%4s" %loopno, " ", this_document.split_count, this_document.merger_count, file=outfile2)
		print("%4s" %loopno, " ", this_document.split_count, this_document.merger_count)
	
	
	#-----------------------------#
	#       output results 		  #	
	#-----------------------------#
	#if loopno == 0  or  loopno == 10 or loopno == 20 or  loopno == 100 or loopno == NumberOfIterations -1:
	if loopno == NumberOfIterations -1:

		for line in this_document.line_object_list:
 			# computes cost for entire line using information recorded in line and segment objects; does not change parse.
			for piece in line.pieces:
				assert(piece in this_document.segment_object_dictionary)		# there should be no "new" pieces
			this_document.compute_parsedline_cost(line)		


		print("----------------------------------------\nLoop number:", loopno, file=outfile1)
		print("----------------------------------------", file=outfile1)		# filename "word_list.txt"
		#this_document.print_parsed_lines(outfile1)								# displays text and also total line cost, detailed by segment and cost component
		this_document.print_parsed_lines_textonly(outfile1)						# "textonly" makes it easier to see diffs during development

		print("----------------------------------------\nLoop number:", loopno, file=outfile)
		print("----------------------------------------", file=outfile)			# filename "gibbs_pieces.txt"			
		this_document.print_segment_counts(outfile)
		
# CLOSE OUTPUT FILES SO THAT INFORMATION DERIVED BY PROGRAM CAN BE VIEWED DURING INTERACTIVE QUERIES
outfile2.close()
outfile1.close()
outfile.close() 


while (True):
	command = input("Enter word:")
	if len(command)==0:
		print("enter a word.")
		continue
	if command =="exit"  :
		break

	this_document.test_unbroken_text(command)

