#!/usr/bin/env python3

import sys
import os
import random
import math
g_encoding = "asci"  # "utf8"
shift_counter = []

#morphemes = {}
#totalmorphemecount = 0.0
random.seed(a=5)    # audrey  2015_12_09  #Note that integer seed is not affected by seed change in python3

# PARAMETERS   # probably want shorter segments initially (so BREAKPROB higher than 0.1)
BitsPerLetter = 5
BREAKPROB     = 0.1		# 0.5  #0.4 #0.3  #0.2    # 0.1   # where does this probability come from? is it a statistic about languages in general/English?
DEFAULTCOUNT  = 1		# 0.5  # Used in GetCount()   tbd  2016_01_09
PLOGCOEFF     = 10		# used in both GetSegmentCost() and EvaluateWordCost()
						# expect redesign in future


## ---------------------------------------------------------------------------------------##
class Segment:   # think type, not token   <morpheme>  <word-type>
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


	def get_plog(self, totalsegmentcount):    # IS THERE ANY REASON TO RETURN PLOG? MAYBE JUST SET IT?  PERHAPS CALL IT set_plog
		if self.count >= 1:
			return math.log( (totalsegmentcount / float(self.count)), 2 )     # BUT WHAT IF segment not in dictionary?
		else:
			return math.log( (totalsegmentcount / float(DEFAULTCOUNT)), 2 )  # MAYBE ! Have to think and experiment

				
	def get_plog_charge(self, totalsegmentcount):
		return PLOGCOEFF * self.get_plog(totalsegmentcount)

		
	def get_instance_cost(self, totalsegmentcount):
		return self.get_plog_charge(totalsegmentcount) + self.sum_dictcosts_portion
		

## ---------------------------------------------------------------------------------------##
class Line:     # a bounded expression  <word in dx1 file>    <line in corpus>
## ---------------------------------------------------------------------------------------##
	def __init__(self, unbroken_text):
		self.unbroken_text              = unbroken_text      # (former self.word)
		self.true_text                  = []		# depends whether we derive unbroken from true or just read unbroken directly
		self.breaks                     = []
		self.pieces                     = []		# list of strings  <morphs>   <words>   NOT segment objects 

		self.piecesorder_cost			= 0.0		# Since only local information is needed for parsing decisions,
		self.total_cost 		        = 0.0		# total_cost for the line and the lists below are not maintained at intermediate stages.
													# Use self.EvaluateLineParse() to obtain (and if desired display) line cost information.

		self.phonocost_portion_list 	= []		# List per segment of phonocost_portion, in proper order. Similarly for other list variables.
		self.ordercost_portion_list     = []		# The lists are used to arrange segment information attractively for display.
		self.inclusioncost_portion_list = []		# Are they useful to retain? Should they be in a separate Display class?
		self.plog_list 		            = []
		self.subtotal_list              = []		# list per segment of following quantity: 
													# ordercost_portion + phonocost_portion + inclusioncost_portion + plog
		
		
		
#	def partialcopy(self, other):       # NOT NEEDED
#		self.unbroken_text = other.unbroken_text
#		self.true_text = other.true_text      # Questionable - this would be extra work
#		self.breaks = other.breaks[:]


#	def addcut(self, point):            # DO WE WANT THIS ?  Fix breaks and morphs at same time--here, not in separate call.
#		AddIntegerToList(point, self.breaks)	 


#	def removecut(self, this_point):    # DO WE WANT THIS ?
#		try:
#			self.breaks.remove(this_point)
#		except ValueError:
#			pass


	def getpiece(self, pieceno):   # NOTICE THERE IS A DIFFERENT FUNCTION GetPiece()
		return self.unbroken_text[self.breaks[pieceno-1]:self.breaks[pieceno]]     # use "breakno" instead of "pieceno"
		

	def displaytextonly(self, outfile):
		FormatString1 = "%20s"       # USE ALSO FormatString3?  space befire breaks? call this in display? in displaytoscreen? combine?
		print(self.unbroken_text, " breaks:",  self.breaks, file=outfile)
		print("  pieces:", end=' ', file=outfile)	 # FIX SPACING?	 
		for n in range(1,len(self.breaks)):
			print(self.getpiece(n), "", end=' ', file=outfile)    # note the comma for continuation
		print(file=outfile)
	

	def display(self, outfile):
		FormatString1 = "%20s"
		FormatString2 = "%8.1f"
		FormatString3 = "%8s"

		#Total = 0
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

		#Total = 0
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
		 
 
 
#----------------------------------------------------------#
	# for the first breakpoint that is greater than or equal to the point, return the breakpoint and its index

	def break_cover(self, point):	
		if point not in range(1, len(self.unbroken_text)):
			print("Error in break_cover(): point (=", point, ") must satisfy 0 < point < ", len(self.unbroken_text), "for line = '", self.unbroken_text, "'.")
			sys.exit()
		for n in range(1, len(self.breaks)):     # Note self.breaks[0] = 0.  
			if point <= self.breaks[n]:
				return (self.breaks[n], n)
		return (-1, -1)   #should never happen!          
#----------------------------------------------------------#   NOT CALLED
# for the first break that is greater than or equal to the point, return the morpheme preceding the break, for comparison w/ new morpheme
#
#	def GetPieceFromLetterNumber( point ):
#		for n in range(1,len(self.breaks)):
#			if point <= self.breaks[n]:
#				return (n,word[self.breaks[n-1]:self.breaks[n]])
#		return (-1,-1)
#
#
#----------------------------------------------------------#
#----------------------------------------------------------#
 
#----------------------------------------------------------#
## ---------------------------------------------------------------------------------------##
##		End of class Line:
## ---------------------------------------------------------------------------------------##

 
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




	def print_parsed_lines_textonly(self, outfile):
		for line in self.line_object_list:
			line.displaytextonly(outfile)	# displays only unbroken line and its parse
	
	
	def print_segment_counts(self, outfile):
		# count information is stored in the segment_object_dictionary,
		# along with other information which will not be displayed
		
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
			print("Error in fetch_plogged_segment_from_dictionary: if segment is in the dictionary, its count should not be 0")
			sys.exit()		
		this_segment.plog = math.log( self.totalsegmentcount / float(this_segment.count), 2 )
		return this_segment

		
#	def create_zerocount_segment(self, piece):  # used for considering cost of a hitherto unseen sesgment
#		this_segment = Segment(piece, 0)
#		this_segment.fill_portion_costs(DEFAULTCOUNT)
#		this_segment.plog = math.log( self.total_segmentcount / DEFAULTCOUNT, 2 )
#		return this_segment
		

	def new_segment_object(self, piece, count):
		this_segment = Segment(piece)
		this_segment.count = count
		this_segment.divide_charges_among_instances()   # replaces 0 by DEFAULTCOUNT
		this_segment.plog = this_segment.get_plog(self.totalsegmentcount)		# replaces 0 by DEFAULTCOUNT
		return this_segment

		
	def increment_count(self, piece):
		dictionary = self.segment_object_dictionary
		if not piece in dictionary:
			dictionary[piece] = self.new_segment_object(piece, 1)
		else:
			dictionary[piece].count += 1	# N.B. For efficiency, the member variables that depend on the count
											# are not updated here. The developer must be aware of this and take
											# care to update those values as soon as the particular counting 
											# operation is completed. 

	
	def initial_segmentation(self):
		for ln in self.line_object_list:
			start = 0		 
			ln.breaks.append(0)								# always put a break at the beginning
			for n in range(1, len(ln.unbroken_text)):		# won't randomly put a break at the beginning or end
				if random.random() < BREAKPROB:				# about every 10 (= 1/BREAKPROB) letters add a break
					piece = ln.unbroken_text[start:n]
					ln.pieces.append(piece)
					ln.breaks.append( n )
					start = n	
					#IncrementCount(piece, self.segment_object_dictionary)  # increment piece in global morphemes dictionary
					#totalmorphemecount += 1 #len(piece)
					self.totalsegmentcount += 1
					self.increment_count(piece)    # keep track in the segment_object_dictionary
					
			if start < len(ln.unbroken_text):      # should always be true...
				piece = ln.unbroken_text[start:]
				ln.pieces.append(piece)
				ln.breaks.append( len(ln.unbroken_text) )   # always put a break at the end
				self.totalsegmentcount += 1
				self.increment_count(piece)


		# Now that forming of segments is complete, 
		# fill in the information that depends on their count.	 
		for piece, sgmt in self.segment_object_dictionary.items():  # maybe just   .values()
			sgmt.divide_charges_among_instances()
			sgmt.get_plog(self.totalsegmentcount)
	


	def compare_alt_parse(self, line):
	
		point = random.randrange( 1, len(line.unbroken_text))	# selects a point to consider splitting at, not beginning or end
		#point = 1 + int(random.random() * (len(line.unbroken_text)-1))	 # agrees with behavior of random.randrange prior to python3
		#print("point =", point)  # randrange changed in python3, so output doesn't match pre-python3 runs. Using random.random() as shown DOES exactly reproduce pre-python3 results, except for spacing and ordering.
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

				
				# May want to display line as it was, then as it is after the split
				# (either for the entire line or for the local change)
				

		
		# Merging:
		elif point == line.breaks[breakindex]:								# so point is the first character within its piece

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
				
				# May want to display line as it was, then as it is after the merge
				# (either for the entire line or for the local change)
				
					
		#return (split_count, merger_count)


#	def EvaluateWordParse(self,morphemes,totalmorphemecount):
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
		

#----------------------------------------------------------#
#----------------------------------------------------------#

## ---------------------------------------------------------------------------------------##
##		End of class Document:
## ---------------------------------------------------------------------------------------##





#def PrintTopMorphemes(WordObjectList, outfile,threshold):
#	print("Dictionary:\n", file=outfile)
#	morphemes = {}
#	for word in WordObjectList: 	
#		for n in range(1,len(word.breaks)):		 
#			piece = word.getpiece(n)	 		
#			IncrementCount(piece, morphemes)
# 
#	pieces = sorted (morphemes, key = morphemes.get, reverse = True  ) # sort by value
#
#	for n in range(len(morphemes)):	
#		morph = pieces[n]
#		if morphemes[morph] <= threshold:
#			break
#		print(n, morph , morphemes[morph], file=outfile)
##		if not morph in BestMorphemes:
##			BestMorphemes[morph] = []
##		BestMorphemes[morph].append((loopno, morphemes[morph] ))
#
##	for morph in BestMorphemes.keys():
##		print >>outfile, morph, BestMorphemes[morph]

#----------------------------------------------------------#
 
#def PrintAllLines (line_object_list, myoutfile, label):

#	print("----------------------------------------\n", file=myoutfile)
#	print("Line List:", label , "\n", end=' ', file=myoutfile)
#	print("----------------------------------------\n", file=myoutfile)

#	for line in line_object_list:
#		line.display(myoutfile)          # displays parse and cost information 
		
	# NOTE
		# The textonly version (next) is useful for seeing the effect of development changes.
		# The full display may then be used to analyze specific examples.

#----------------------------------------------------------#

#def PrintAllLines_textonly (line_object_list, myoutfile,label):

#	print("----------------------------------------\n", file=myoutfile)
#	print("Line List:", label , "\n", end=' ', file=myoutfile)
#	print("----------------------------------------\n", file=myoutfile)

#	for line in line_object_list:
#		line.displaytextonly(myoutfile)   # displays only unbroken line and its parse
#		#line.display(myoutfile)          # displays also cost information  

#----------------------------------------------------------#
# returns the position of point in sorted list numberlist, returns -1 if point is not in numberlist
#def positionInBreaks(point, numberlist):	 
#	for n in range(0,len(numberlist)):
#		if numberlist[n] == point:
#			#print "position found: ", n
#			return n
#		if numberlist[n] > point:
#			return -1
#	return -1
#----------------------------------------------------------#  REWROTE THIS AS A Line FUNCTION
# returns index in sorted numberlist of "least upper bound" of point--that is, returns index of first entry which is >= point
# returns -1 if point exceeds all entries
#def covering_index(point, numberlist):	 
#	for n in range(0,len(numberlist)):
#		if numberlist[n] == point:
#			#print "position found: ", n
#			return n
#		if numberlist[n] > point:
#			return n
#	return -1   #should never happen!          
#----------------------------------------------------------#
# adds integer point to numberlist, keeping list sorted, returns the index it inserted it at
#def AddIntegerToList(point, numberlist):		#expects that point is less than the last number in numberlist
#	if len(numberlist) == 0:
#		numberlist.append(point)
#	for n in range(0,len(numberlist)):		
#		if numberlist[n] > point:
#			numberlist.insert(n,point)
#			return n
#	return -1
#----------------------------------------------------------#
#def GetPiece(piecenumber, word, numberlist):     # NOTICE THERE IS A DIFFERENT FUNCTION getpiece()
#	return word[numberlist[piecenumber-1]: numberlist[piecenumber]]   # should use breaknumber. morph which goes up to break[breaknumber] is actually morphs[breaknumber-1]
#----------------------------------------------------------#
#def GetPlog(morpheme, morphemes, totalmorphemecount):

##	if morpheme in morphemes:
##		thiscount = morphemes[morpheme]
##	else:
##		thiscount = 1

#	thiscount = GetCount(morpheme, morphemes)	# tbd  2016_01_09  audrey
#	return math.log( totalmorphemecount / float( thiscount ) , 2 )
#----------------------------------------------------------#
#def RecountMorphemes(WordObjectList):   #was (WordObjectList, morphemes)       audrey  2015_12_17
#	newmorphemes = {}
#	for word in WordObjectList:		 
#		for n in range(1, len(word.breaks)):	#was range(len(word.breaks))   audrey  2015_12_17		 
#			piece = word.getpiece(n)
#			IncrementCount(piece,newmorphemes)
#	return newmorphemes
		
#----------------------------------------------------------#
#def ComputeTotalMorphemeCount(morphemes):
#	totalmorphemecount = 0
#	for item in morphemes:
#		totalmorphemecount += float(morphemes[item]) # why float? is it because needed for division in plog?
#	return totalmorphemecount


#----------------------------------------------------------#
#def GetCount(item, dictionary):
#	# defaultcount = 0.5   # 0.25 # 1   #defaultcount set now in parameters section at top of file
#	if not item in dictionary:
#		return defaultcount
#	else:
#		return dictionary[item]
#----------------------------------------------------------#
#def IncrementCount(item, dictionary):    
#	if not item in dictionary:
#		dictionary[item] = 1
#	else:
#		dictionary[item] += 1
#----------------------------------------------------------#
#def GetSegmentCost(morph, morphemes, totalmorphemecount):
#	# NOTE - DEPENDENT ON PARAMETERS defaultcount, plogcoeff
#	
#	data_cost = plogcoeff * GetPlog(morph, morphemes, totalmorphemecount)
#	dictionary_phonological_cost = len(morph) * float(BitsPerLetter)
#	dictionary_order_cost = math.log (math.factorial(len(morph)), 2)
#	dictionary_list_cost = 1.0    # audrey   WHY?
#	
#	segment_cost = data_cost + (dictionary_phonological_cost + dictionary_order_cost + dictionary_list_cost)/GetCount(morph, morphemes)
#	return segment_cost
#----------------------------------------------------------#
#def IncrementCountAmount(item, dictionary, amount):
#	if not item in dictionary:
#		dictionary[item] = amount
#	else:
#		dictionary[item] += amount
#----------------------------------------------------------#
  
#----------------------------------------------------------#

#def ConsolePrint (word):
#	print(word, end=' ')
#	if word not in breaks:
#		"Word not found." 
#		return
#	for n in breaks[word]:		
#		if n==0:
#			previous = n
#			continue		 
#		print(word[ previous: n ], end=' ')
#		previous = n
#	print()





#----------------------------------------------------------#
# this is not currently being used: 
#----------------------------------------------------------#

#def ShiftBreak (word, thiswordbreaks, shiftamount, outfile, totalmorphemecount):
#	ShiftFormatString1 = "\nShifting.   %20s %35s %12s %12s %12s  %12s -    Old score %7.1f newscore: %5.1f " 
#	ShiftFormatString2 = "                                                                      plog: %5.1f        %5.1f        %5.1f	    %5.1f" 
#	ShiftFormatString3 = "                                                             log factorial: %5.1f        %5.1f        %5.1f         %5.1f" 
#	splitword = []
#	newwordbreaks = []
#	start = 0
	
#	#if there are any breaks in middle of word, pick a break point and shift it.
#	if shiftamount > 0:
#		if len(thiswordbreaks) <= 2:
#			return (False, thiswordbreaks)
#		else:
#			breakindex = random.randrange(1, len(thiswordbreaks)-1)
#		if thiswordbreaks[breakindex + 1] <= thiswordbreaks[breakindex] + shiftamount:	# this means the next breakpoint is too close to consider this shift
#			return (False, thiswordbreaks);
#	if shiftamount < 0:
#		if len(thiswordbreaks) <= 2:
#			return (False, thiswordbreaks)
#		else:
#			breakindex = random.randrange(1, len(thiswordbreaks)-1)
#		if thiswordbreaks[breakindex - 1] >= thiswordbreaks[breakindex] + shiftamount:	# this means the next breakpoint is too close to consider this shift
#			return (False, thiswordbreaks);

#	for n in range(1, len(thiswordbreaks) ):				#breaks is a list of integers indicating morpheme breaks
#		splitword.append( word[start: word.breaks[n] ] )	# splitword is a list of the morphemes
#		start = thiswordbreaks[n]	 
#	# info about old pieces
#	OldLeftPiece  			= GetPiece( breakindex, word, thiswordbreaks )
#	OldRightPiece 			= GetPiece( breakindex+1, word,  thiswordbreaks )
#	count1 				= GetCount(OldLeftPiece,morphemes)
#	phonologicalcostOldLeftPiece 	= BitsPerLetter * len(OldLeftPiece) / float(count1)
#	logfacOldLeftPiece 		= math.log( math.factorial( len(OldLeftPiece) ) , 2 )				
#	count2 				= GetCount (OldRightPiece, morphemes)
#	phonologicalcostOldRightPiece 	= BitsPerLetter * len(OldRightPiece) / float(count2)
#	logfacOldRightPiece		= math.log( math.factorial( len(OldRightPiece) ) , 2 )	
#	oldplogLeft 			= GetPlog ( OldLeftPiece, morphemes, totalmorphemecount)
#	oldplogRight 			= GetPlog ( OldRightPiece, morphemes, totalmorphemecount)
#	oldscore   			= oldplogLeft + oldplogRight + logfacOldLeftPiece  + logfacOldRightPiece +    phonologicalcostOldLeftPiece + phonologicalcostOldRightPiece

#	# info about new pieces
#	newwordbreaks 			= thiswordbreaks[:]
#	newwordbreaks[breakindex]	+= shiftamount

#	NewLeftPiece   			= GetPiece( breakindex, word, newwordbreaks )
#	count1 				= GetCount (NewLeftPiece, morphemes)	
#	phonologicalcostNewLeftPiece 	= BitsPerLetter * len(NewLeftPiece) / float(count1)
#	logfacNewLeftPiece 		= math.log(math.factorial( len(NewLeftPiece) ) , 2 )	

#	NewRightPiece   		= GetPiece (breakindex + 1, word, newwordbreaks) 
#	count2 				= GetCount (NewRightPiece, morphemes)
#	phonologicalcostNewRightPiece 	= BitsPerLetter * len(NewRightPiece) / float(count2)
#	logfacNewRightPiece 		= math.log(math.factorial( len(NewRightPiece) ) , 2 )	
 
#	newplogLeft 			= GetPlog(NewLeftPiece, morphemes,totalmorphemecount)
#	newplogRight 			= GetPlog(NewRightPiece, morphemes,totalmorphemecount)
#	newscore   			= newplogLeft + newplogRight +  logfacNewLeftPiece + logfacNewRightPiece    + phonologicalcostNewLeftPiece + phonologicalcostNewRightPiece

#	start = 0
#	newsplitword = []
#	for n in range(1, len(newwordbreaks) ):				#breaks[word] is a list of integers indicating morpheme breaks
#		newsplitword.append( word[start: newwordbreaks[n] ] )	# splitword is a list of the morphemes
#		start = newwordbreaks[n]

#	if newscore < oldscore:
#		if False:
#			print("shifting " + ' '.join(splitword) + ' to ' + ' '.join(newsplitword))
#			shift_counter.append(1)
#			print(ShiftFormatString1 % (word, splitword, OldLeftPiece, OldRightPiece, NewLeftPiece, NewRightPiece, oldscore, newscore ))	
#			print(ShiftFormatString2 %(  oldplogLeft , oldplogRight, newplogLeft, newplogRight)) 		 				 
#			print(ShiftFormatString3 %(  logfacOldLeftPiece , logfacOldRightPiece, logfacNewLeftPiece, logfacNewRightPiece)) 
#		return (True, newwordbreaks )
#	return (False, thiswordbreaks)	









 
#------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------#









#--------------------------------------------------------------------##
#		Main program    This will be  def main(   )
#--------------------------------------------------------------------##

#---------------------------------------------------------#
#	1. File input, output
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
 
#------------------------------------#

# INITIAL PROCESSING   --  Input and everything preceding iterative processing.
# Once jsonpickle is set up,
# this section and loading from a saved state (in order to resume processing) will be alternatives.

this_document = Document()					

# Will need user to specify whether input is word list or corpus. Then may handle input via a Document function instead of inline as here.

# THIS PART IS FOR READING FROM dx1 FILE   (not yet reworked for new class structure  2016_01_21)
#filelines= infile.readlines()
#WordCounts={}

# add counts for all words in dictionary
#for line in filelines:
#	pieces = line.split(' ')
#	word=pieces[0] # the first column in the dx1 file is the actual word 
#	word = ''.join([c.lower() for c in word if c not in "()1234567890"])
#	if word in WordCounts:
#		WordCounts[word] += 1
#	else:
#		WordCounts[word]= 1

#print "We read", len(WordCounts), "words." 
# saves words also in list format, then sorts alphabetically (in case they're not already?)
#wordlist = WordCounts.keys()
#wordlist.sort()

# THIS PART IS FOR READING CORPUS
textline_list = infile.readlines()
for textline in textline_list:
	this_document.line_object_list.append(Line(textline))  # try it! If it doesn't work, uncomment next 2 lines instead
	#this_line = Line(textline)
	#this_document.line_object_list.append(this_line)
print("There are ", len(this_document.line_object_list), "lines in this document")

#---------------------------------------------------------#
#	End of file input, output
#---------------------------------------------------------#







#---------------------------------------------------------#
#	2. Random splitting of words
#---------------------------------------------------------#
 
#totalmorphemecount = 0  # number of morphemes, counting duplicates   # these are now set by __init__
#WordObjectList = [] # this is a list of objects of class class_word

# introduce initial breaks at random within each line;
# enter into the dictionary occurrence counts and other information for the resulting segments
# make dictionary entries for the resulting segments

this_document.initial_segmentation()
print("End of initial randomization.") 




#----------------------------------------------------------#
#		3. Main loop
#----------------#----------------------------------------------------------#------------------------------------------#
NumberOfIterations = 25  # 20000  # 160			# 200 seems to be a good number
print("Number of iterations: ", NumberOfIterations)
LoopNumberAtWhichWeStartTracking = 20

# Markov chain based on sampling individual components (i.e., distribution of individual segment conditioned on the other segments)
for loopno in range (NumberOfIterations):
	#print >>outfile, "loop number", loopno
	#print loopno     #commented out here because loopno now appears onscreen with split and merger counts
	
	this_document.split_count = 0
	this_document.merger_count = 0
	
	for line in this_document.line_object_list:
		this_document.compare_alt_parse(line)

	#if this_document.split_count + this_document.merger_count > 0:
	if True:
		print("%4s" %loopno, " ", this_document.split_count, this_document.merger_count, file=outfile2)
		print("%4s" %loopno, " ", this_document.split_count, this_document.merger_count)

	# recalculate morpheme frequencies & number of morphemes
	#morphemes = RecountMorphemes(WordObjectList)					# NOT NEEDED (I think)  
	#totalmorphemecount = ComputeTotalMorphemeCount(morphemes)		# EXCEPT MAYBE TO CHECK THAT UPDATES WERE DONE CORRECTLY
	
	#----------------------------------------------------------#
	#       output intermediate results 			   #	
	#----------------------------------------------------------#
	#if loopno == 0  or  loopno == 10 or loopno == 20 or  loopno == 100 or loopno == NumberOfIterations -1:
	if loopno == NumberOfIterations -1:

 		# COMPUTES COSTS FOR ENTIRE LINE USING CURRENT RECORDED COUNTS. DOES NOT CHANGE PARSE.
 		# (Currently costs are not displayed in output. Subject to change in future, especially in an interactive mode.)
		for line in this_document.line_object_list:
			for piece in line.pieces:
				assert(piece in this_document.segment_object_dictionary)		# at this point, there should be no "new" pieces
			this_document.compute_parsedline_cost(line)		

 
		# first: print ALL words, with their analysis.
		print("----------------------------------------\nLoop number:", loopno, file=outfile1)
		print("----------------------------------------", file=outfile1)
		#PrintAllWords(WordObjectList,outfile1,loopno)				# outfile1 is "word_list.txt"
		this_document.print_parsed_lines_textonly(outfile1)			# "textonly" makes it easier to see parse diffs   audrey  2015_12_21
		print("----------------------------------------\nLoop number:", loopno, file=outfile)
		print("----------------------------------------", file=outfile)
		#threshold = 0
		#PrintTopMorphemes(WordObjectList, outfile,threshold)   # outfile is "gibbs_pieces.txt"
		this_document.print_segment_counts(outfile)	# outfile is "gibbs_pieces.txt"
		


# MOVED UPWARD TO HERE SO THAT PERSON DOING INTERACTIVE QUERIES CAN VIEW THE INFORMATION DERIVED BY PROGRAM
outfile2.close()
outfile1.close()
outfile.close() 


CommandList=list()
while (True):
	command = input("Enter word:")
	CommandList.append(command)
	#command_words = command.split()
	if len(command)==0:
		print("enter a word.")
		continue
	if command =="exit"  :
		break
	#ConsolePrint(command)

	#object_word = class_word(command)
	#object_word.TestUnbrokenWord(morphemes, totalmorphemecount)

	this_document.test_unbroken_text(command)

 #----------------------------------------------------------#
 #	4. Print results
 #----------------------------------------------------------#

#MinimumOccurrenceCount = 3   # if there are less than 3 occurrences of a morpheme, it probably doesn't mean much
#PrintTopMorphemes(WordObjectList, outfile, MinimumOccurrenceCount)
#PrintAllWords(WordObjectList, outfile1, "Final")
