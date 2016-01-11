#!/usr/bin/python

import sys
import os
import random
import math
import copy
g_encoding = "asci"  # "utf8"
shift_counter = []

morphemes = {}
totalmorphemecount = 0.0
random.seed(a=5)    # audrey  2015_12_09

BitsPerLetter = 5   # moved upward   audrey  2015_12_16
loopno = 0
split_count = 0
merger_count = 0

plogcoeff = 5  #3
# ordercoeff = 2

## ---------------------------------------------------------------------------------------##
class class_word:
## ---------------------------------------------------------------------------------------##
	def __init__(self, this_word):
		self.word = this_word
		self.id = 0                                     # to help with debugging
		
		self.TotalLogFacPieces 	= 0
		self.TotalPlogs 	= 0
		self.TotalPhonologicalCost = 0
		self.TotalCost 		= 0
		self.WordLogFacLength 	= 0.0
		self.TotalMorphemeListLengthCosts = 0.0
		self.LogFacList 	= []
		self.PlogList 		= []
		self.PhonologicalCostList= []
		self.MorphemeListLengthCostList 	= []		# marginal cost of having one more morpheme on this list
		self.SubtotalList= []
		self.breaks = []
		self.morphs = []
 
 

	def partialcopy(self, other):
		self.word = other.word		 
		self.breaks = other.breaks[:]
	def addcut(self, point):
		AddIntegerToList(point, self.breaks)	 
	def removecut(self, this_point):
		try:
			self.breaks.remove(this_point)
		except ValueError:
			pass
	def getpiece(self, pieceno):
		return self.word[self.breaks[pieceno-1]:self.breaks[pieceno]]
		
	def displaytextonly(self, outfile):
		FormatString1 = "%20s"
		print >>outfile, self.word,"  breaks:",  self.breaks
		print >>outfile, "  morphs:",		 
		for n in range(1,len(self.breaks)):
			print >>outfile, self.getpiece(n), "",    # note the comma for continuation
		print >>outfile
	
	def display(self, outfile):
		FormatString1 = "%20s"
		FormatString2 = "%8.1f"
		FormatString3 = "%8s"
		 

		Total = 0

		print >>outfile,"\n", self.word,"breaks:",  self.breaks
		
		print >>outfile, FormatString1 %("morphs:"),		 
		for n in range(1,len(self.breaks)):
			print >>outfile, FormatString3 %(self.getpiece(n)),
		print >>outfile

 		print >>outfile, FormatString1 %("plog:"),	
		for item in self.PlogList:
			print >>outfile,FormatString2 %(item),
		print >>outfile
 		print >>outfile, FormatString1 %("log |piece|!:"),	
		for item in self.LogFacList:
			print >>outfile,FormatString2 %(item),
		print >>outfile
		print >>outfile, FormatString1 %("phono info:"),	
		for item in self.PhonologicalCostList:
			print >>outfile,FormatString2 %(item),
		print >>outfile

		print >>outfile, FormatString1 %("morpheme list cost:"),	
		for item in self.MorphemeListLengthCostList:
			print >>outfile,FormatString2 %(item),
		print >>outfile
		print >>outfile, FormatString1 %("subtotal:"),	
		for item in self.SubtotalList:
			print >>outfile,FormatString2 %(item),
			Total += item
		print >>outfile

		logfacword = self.WordLogFacLength
		print >>outfile, FormatString1 %("log |word|!:"),
		print >>outfile,FormatString2 %( logfacword ),
		print >>outfile
		#print >>outfile, FormatString1 %("List cost:"),
		#print >>outfile,FormatString2 %( self.TotalMorphemeListLengthCosts ),
		#print >>outfile
		print >>outfile, FormatString1 %("Total:"),
		print >>outfile,FormatString2 %( self.TotalCost  )
	def displaytoscreen(self):
		FormatString1 = "%20s"
		FormatString2 = "%8.1f"
		FormatString3 = "%8s"
		 

		Total = 0

		print  self.word, "breaks", self.breaks
		
		print FormatString1 %("morphs:"),		 
		for n in range(1,len(self.breaks)):
			print FormatString3 %(self.getpiece(n)),
		print 

 		print FormatString1 %("plog:"),	
		for item in self.PlogList:
			print FormatString2 %(item),
		print 
 		print FormatString1 %("log |piece|!:"),	
		for item in self.LogFacList:
			print FormatString2 %(item),
		print 
		print FormatString1 %("phono info:"),	
		for item in self.PhonologicalCostList:
			print FormatString2 %(item),
		print 

		print FormatString1 %("morpheme list cost:"),	
		for item in self.MorphemeListLengthCostList:
			print FormatString2 %(item),
		print 
		print FormatString1 %("subtotal:"),	
		for item in self.SubtotalList:
			print FormatString2 %(item),
			Total += item
		print 

		logfacword = self.WordLogFacLength
		print FormatString1 %("log |word|!:"),
		print FormatString2 %( logfacword ),
		print 
		#print FormatString1 %("List cost:"),
		#print FormatString2 %( self.TotalMorphemeListLengthCosts ),
		#print 
		print FormatString1 %("Total:"),
		print FormatString2 %( self.TotalCost  )

		 
 
 
#----------------------------------------------------------#
# for the first break that is greater than or equal to the point, return the morpheme preceding the break, for comparison w/ new morpheme

	def GetPieceFromLetterNumber( point ):
		for n in range(1,len(self.breaks)):
			if point <= self.breaks[n]:
				return (n,word[self.breaks[n-1]:self.breaks[n]])
		return (-1,-1)


#----------------------------------------------------------#
#----------------------------------------------------------#

	def EvaluateWordParse(self,morphemes,totalmorphemecount):
		#self.TotalLogFacPieces 	= 0
		#self.TotalPlogs 	= 0
		#self.TotalPhonologicalCost 	= 0
		#self.TotalListCost 	= 0
		#self.TotalCost 		= 0
		#self.LogFacList 	= []
		#self.PlogList 		= []
		#self.PhonologicalCostList = []
		#self.morphs		= []
		#self.totalmorphcostList = []
		#self.TotalMorphemeListLengthCosts = 0.0
		#self.MorphemeListLengthCostList	= []
		#self.SubtotalList	= []
		splitword = []    # a list of the morphemes in a word
		start = 0         # what index the morpheme starts at
		# fills splitword with the current morphemes
		for n in range( 1,len(self.breaks) ):			#breaks[word] is a list of integers indicating morpheme breaks
			self.morphs.append( self.word[start: self.breaks[n] ] )	#   list of the morphemes
			start = self.breaks[n]
		self.WordLogFacLength =  math.log (math.factorial(len(self.morphs)), 2)    # audrey  Why factorial? Isn't order known via breaks?
		for morph in self.morphs:   # !!!  SHOULD USE GetSegmentCost()  !!!   audrey
			#LogFacPiece =  math.log (math.factorial(len(morph)), 2)    # audrey  In coursenotes, this cost is shared by occurrences of morph
			LogFacPiece =  math.log (math.factorial(len(morph)), 2)/GetCount(morph,morphemes)   # Try it!  audrey  2015_12_11
			self.LogFacList.append(LogFacPiece)	
			self.TotalLogFacPieces += LogFacPiece
	
			#PlogPiece = 10 * GetPlog(morph, morphemes, totalmorphemecount)  # Why 10?  Try it without.  audrey  2015_12_02  
			PlogPiece = plogcoeff * GetPlog(morph, morphemes, totalmorphemecount)  # 5  2   audrey  2015_12_11  
			#PlogPiece = GetPlog(morph, morphemes, totalmorphemecount)  
			self.TotalPlogs += PlogPiece
			self.PlogList.append(PlogPiece)
		
			PhonologicalCost = len(morph) * float(BitsPerLetter)/GetCount(morph,morphemes)
			self.TotalPhonologicalCost += PhonologicalCost
			self.PhonologicalCostList.append(PhonologicalCost)
	
 
			CostOfHavingMorphOnMorphList = 1.0/GetCount(morph,morphemes)    # audrey   WHY?
			self.MorphemeListLengthCostList.append (CostOfHavingMorphOnMorphList)
			self.TotalMorphemeListLengthCosts += CostOfHavingMorphOnMorphList

			self.SubtotalList.append( LogFacPiece + PlogPiece + PhonologicalCost + CostOfHavingMorphOnMorphList ) 		
		
	 

		self.TotalCost = self.WordLogFacLength + self.TotalLogFacPieces + self.TotalPlogs + self.TotalPhonologicalCost +  self.TotalMorphemeListLengthCosts
		return  

#----------------------------------------------------------#
#----------------------------------------------------------#

	def CompareAltParse(self):   #self is a word_object
		#this_word = copy.deepcopy(self)  # We need this to display the present parse if the alt parse replaces it.
	
		point = random.randrange( 1, len(self.word))	 # selects a point to consider splitting at, not beginning or end
		# spanlist = neighbors(point, self.breaks)
		breakindex = covering_index(point, self.breaks)
		if breakindex == -1:
			print "For record with id =", self.id, ": randomly selected point (=", point, ") is greater than all entries in breaks list. Either point or breaks list is incorrect."
			return
		
		# Splitting:
		#if len(spanlist) == 2: # we compare present parse to an alternative parse in which there is a break at this point
		#if point not in spanlist: # we compare present parse to an alternative parse in which there is a break at this point
		if point < self.breaks[breakindex]:

			# local contribution as presently configured
			left_break = self.breaks[breakindex-1]
			right_break = self.breaks[breakindex]
			unbroken_morph = self.word[left_break:right_break]
			present_contribution = GetSegmentCost(unbroken_morph, morphemes, totalmorphemecount) # here we calculate it; should really just look it up

			# alternative contribution 	
			left_morph = self.word[left_break:point]
			right_morph = self.word[point:right_break]
			alt_contribution = GetSegmentCost(left_morph,  morphemes, totalmorphemecount) + \
			                   GetSegmentCost(right_morph, morphemes, totalmorphemecount) + \
			                   math.log(1 + len(self.morphs), 2)
			logfacword_adjustment = math.log(1 + len(self.morphs), 2)
			                   
			if alt_contribution < present_contribution:
				self.breaks.insert(breakindex, point)    # or use addcut  
				#self.morphs[breakindex-1] = left_morph
				self.morphs.insert(breakindex, right_morph)			                   
				#self.TotalCost = self.TotalCost - present_contribution + alt_contribution

				#self.SubtotalList[breakindex-1] = GetSegmentCost(left_morph,  morphemes, totalmorphemecount)       # TEMPORARY
				#self.SubtotalList.insert(breakindex, GetSegmentCost(right_morph, morphemes, totalmorphemecount))   # TEMPORARY
				
				#self.PlogList[breakindex-1] = 2 * GetPlog(left_morph, morphemes, totalmorphemecount)
				#self.PlogList.insert(breakindex, 2*GetPlog(right_morph, morphemes, totalmorphemecount))
				
				#self.PhonologicalCostList[breakindex-1] = len(left_morph) * float(BitsPerLetter)/GetCount(left_morph,morphemes)
				#self.PhonologicalCostList.insert(breakindex, len(right_morph) * float(BitsPerLetter)/GetCount(right_morph,morphemes))
				
				#self.LogFacList[breakindex-1] = math.log (math.factorial(len(left_morph)), 2)/GetCount(left_morph,morphemes)
				#self.LogFacList.insert(breakindex, math.log (math.factorial(len(right_morph)), 2)/GetCount(right_morph,morphemes))
				
				#self.MorphemeListLengthCostList[breakindex-1] = 1.0/GetCount(left_morph,morphemes)
				#self.MorphemeListLengthCostList.insert(breakindex, 1.0/GetCount(right_morph,morphemes))
				
				#self.WordLogFacLength = self.WordLogFacLength + logfacword_adjustment    # Only because it shows up in display audrey 2015_12_16
				#self.TotalMorphemeListLengthCosts =  #could do an adjustment, but prefer instead to leave it out of the display (since already covered in Subtotals)			

				#if loopno >= LoopNumberAtWhichWeStartTracking:    # I think this will work because they're global
				#if True:    # FOR DEVELOPMENT, PRINT ALL AND DO SAME FOR PREVIOUS VERSION
					#print >>outfile, "Splitting"
					##print "Splitting", wordstring		
					#this_word.display(outfile)
					#self.display(outfile)

		
		# Merging:
		#if len(spanlist) == 2: # we compare present parse to an alternative parse in which there is a break at this point
		#if point not in spanlist: # we compare present parse to an alternative parse in which there is a break at this point
		elif point == self.breaks[breakindex]:
			#print len(self.morphs)

			# local contribution as presently configured
			left_break = self.breaks[breakindex-1]
			right_break = self.breaks[breakindex+1]
			left_morph = self.word[left_break:point]
			right_morph = self.word[point:right_break]
			present_contribution = GetSegmentCost(left_morph, morphemes, totalmorphemecount) + GetSegmentCost(right_morph, morphemes, totalmorphemecount)

			# alternative contribution 	
			unbroken_morph = self.word[left_break:right_break]
			logfacword_adjustment = -math.log(len(self.morphs), 2)
			alt_contribution = GetSegmentCost(unbroken_morph, morphemes, totalmorphemecount) - math.log(len(self.morphs), 2)
			
			if alt_contribution < present_contribution:
				#self.morphs[breakindex-1] = unbroken_morph
				self.morphs.pop(breakindex)
				#self.TotalCost = self.TotalCost - present_contribution + alt_contribution
				
				#self.SubtotalList[breakindex-1] = GetSegmentCost(unbroken_morph, morphemes, totalmorphemecount)   # TEMPORARY
				#self.SubtotalList.pop(breakindex)
				
				#self.PlogList[breakindex-1] = 2 * GetPlog(unbroken_morph, morphemes, totalmorphemecount)
				#self.PlogList.pop(breakindex)
				
				#self.PhonologicalCostList[breakindex-1] = len(unbroken_morph) * float(BitsPerLetter)/GetCount(unbroken_morph,morphemes)
				#self.PhonologicalCostList.pop(breakindex)
				
				#self.LogFacList[breakindex-1] = math.log (math.factorial(len(unbroken_morph)), 2)/GetCount(unbroken_morph,morphemes)
				#self.LogFacList.pop(breakindex)
				
				#self.MorphemeListLengthCostList[breakindex-1] = 1.0/GetCount(unbroken_morph,morphemes)
				#self.MorphemeListLengthCostList.pop(breakindex)
				
				self.breaks.pop(breakindex)
				
				#self.WordLogFacLength = self.WordLogFacLength + logfacword_adjustment    # Only because it shows up in display audrey 2015_12_16

				#If loopno >= LoopNumberAtWhichWeStartTracking:					
				#if True:    # FOR DEVELOPMENT, PRINT ALL AND DO SAME FOR PREVIOUS VERSION
					#print >>outfile, "Merging"
					##print "Merging", wordstring				
					#this_word.display(outfile)
					#self.display(outfile)


#----------------------------------------------------------#
#----------------------------------------------------------#
	#    	audrey  2016_01_08
	# NOTE THAT ORIGINAL CompareAltParse APPEARS ABOVE (AS INTENDED)!
	# MAY WISH TO EDIT OUT THE COMMENTS OR EVEN PUT IN AN ADDITIONAL EDITTED VERSION
	
	def CompareAltParse2(self, split_count, merger_count):   #self is a word_object
		#this_word = copy.deepcopy(self)  # We need this to display the present parse if the alt parse replaces it.
	
		point = random.randrange( 1, len(self.word))	 # selects a point to consider splitting at, not beginning or end
		breakindex = covering_index(point, self.breaks)
		if breakindex == -1:
			print "For record with id =", self.id, ": randomly selected point (=", point, ") is greater than all entries in breaks list. Either point or breaks list is incorrect."
			return
		
		# Splitting:
		if point < self.breaks[breakindex]:

			# local contribution as presently configured
			left_break = self.breaks[breakindex-1]
			right_break = self.breaks[breakindex]
			unbroken_morph = self.word[left_break:right_break]
			present_contribution = GetSegmentCost(unbroken_morph, morphemes, totalmorphemecount) # here we calculate it; should really just look it up

#			# THIS PART IS FOR DEBUGGING
#			print "\nSPLITTING"
#			print "left_break =", left_break, " right_break =", right_break
#			print "unbroken_morph =", unbroken_morph, " count =", GetCount(unbroken_morph, morphemes), \
#				" plog =", GetPlog(unbroken_morph, morphemes, totalmorphemecount), "segment_cost =", present_contribution
#			print "present_contribution =", present_contribution
#			#self.EvaluateWordParse(morphemes, totalmorphemecount)
#			#self.displaytoscreen()

			# THIS PIECE CALCULATES ALT_CONTRIBUTION USING ORIGINAL RANDOMLY CHOSEN POINT
#			# alternative contribution 	
#			left_morph = self.word[left_break:point]
#			right_morph = self.word[point:right_break]
#			alt_contribution = GetSegmentCost(left_morph,  morphemes, totalmorphemecount) + \
#			                   GetSegmentCost(right_morph, morphemes, totalmorphemecount) + \
#			                   math.log(1 + len(self.morphs), 2)
#			logfacword_adjustment = math.log(1 + len(self.morphs), 2)
			
			# Find best alternative contribution
			best_segmentcost = float('inf')
			best_point = left_break
			for test_point in range(left_break + 1, right_break):
				left_morph = self.word[left_break:test_point]
				right_morph = self.word[test_point:right_break]
				test_segmentcost = GetSegmentCost(left_morph,  morphemes, totalmorphemecount) + GetSegmentCost(right_morph, morphemes, totalmorphemecount)
				if test_segmentcost < best_segmentcost:
					best_segmentcost = test_segmentcost
					best_point = test_point

#				# THIS PART IS FOR DEBUGGING
#				print "\ntest_point =", test_point
#				print "left_morph =", left_morph,  " count =", GetCount(left_morph, morphemes), \
#					" plog =", GetPlog(left_morph, morphemes, totalmorphemecount),  "segment_cost =", GetSegmentCost(left_morph,  morphemes, totalmorphemecount)
#				print "right_morph =", right_morph,  " count =", GetCount(right_morph, morphemes), \
#					" plog =", GetPlog(right_morph, morphemes, totalmorphemecount),  "segment_cost =", GetSegmentCost(right_morph,  morphemes, totalmorphemecount)
#				print "test_segmentcost =", test_segmentcost, " best_segmentcost =", best_segmentcost, " best_point =", best_point
				#test_word = copy.deepcopy(self)
				#test_word.breaks.insert(breakindex, test_point)
				#test_word.EvaluateWordParse(morphemes, totalmorphemecount)  # update these?
				#test_word.displaytoscreen()
			    	
			alt_contribution = best_segmentcost + math.log(1 + len(self.morphs), 2)    # last addend is adjustment to present value of log(factorial( len(self.morphs) ))
			point = best_point
			left_morph = self.word[left_break:point]      #not needed    
			right_morph = self.word[point:right_break]    #could wait till below if it turns out that it's needed
#			print "\nbest_point =", best_point, " left_morph =", left_morph, " right_morph =", right_morph
#			print "best_segmentcost =", best_segmentcost
#			print "alt_contribution =", alt_contribution
#			print "present_contribution =", present_contribution
			
			
			# kluge #
#			if morphemes[unbroken_morph] == 1:
#				if GetCount(left_morph, morphemes) <= GetCount(right_morph, morphemes):
#					alt_contribution = alt_contribution - plogcoeff * GetPlog(left_morph, morphemes, totalmorphemecount)
#				else:
#					alt_contribution = alt_contribution - plogcoeff * GetPlog(right_morph, morphemes, totalmorphemecount)
			
			                   
			if alt_contribution < present_contribution:
				split_count = split_count + 1				
				self.breaks.insert(breakindex, point)    # or use addcut  
				self.morphs[breakindex-1] = left_morph
				self.morphs.insert(breakindex, right_morph)			                   


				#if loopno >= LoopNumberAtWhichWeStartTracking:    # I think this will work because they're global
				#if True:    # FOR DEVELOPMENT, PRINT ALL AND DO SAME FOR PREVIOUS VERSION
					#print >>outfile, "Splitting"
					##print "Splitting", wordstring		
					#this_word.display(outfile)
					#self.display(outfile)

#			print "Result of split attempt:"
#			print self.morphs

		
		# Merging:
		#if len(spanlist) == 2: # we compare present parse to an alternative parse in which there is a break at this point
		#if point not in spanlist: # we compare present parse to an alternative parse in which there is a break at this point
		elif point == self.breaks[breakindex]:
			#print len(self.morphs)

			# local contribution as presently configured
			left_break = self.breaks[breakindex-1]
			right_break = self.breaks[breakindex+1]
			left_morph = self.word[left_break:point]
			right_morph = self.word[point:right_break]
			present_contribution = GetSegmentCost(left_morph, morphemes, totalmorphemecount) + GetSegmentCost(right_morph, morphemes, totalmorphemecount)

			# alternative contribution 	
			unbroken_morph = self.word[left_break:right_break]
			logfacword_adjustment = -math.log(len(self.morphs), 2)
			alt_contribution = GetSegmentCost(unbroken_morph, morphemes, totalmorphemecount) - math.log(len(self.morphs), 2)
			
			# kluge #
			# if morphemes[unbroken_morph] == 1:
#			if GetCount(unbroken_morph, morphemes) == 1:
#				if morphemes[left_morph] <= morphemes[right_morph]:
#					present_contribution = present_contribution - plogcoeff * GetPlog(left_morph, morphemes, totalmorphemecount)
#				else:
#					present_contribution = present_contribution - plogcoeff * GetPlog(right_morph, morphemes, totalmorphemecount)
				
			
			if alt_contribution < present_contribution:
				merger_count = merger_count + 1
				#self.morphs[breakindex-1] = unbroken_morph
				self.morphs.pop(breakindex)
				self.breaks.pop(breakindex)
				
				#if loopno >= LoopNumberAtWhichWeStartTracking:					
				#if True:    # FOR DEVELOPMENT, PRINT ALL AND DO SAME FOR PREVIOUS VERSION
					#print >>outfile, "Merging"
					##print "Merging", wordstring				
					#this_word.display(outfile)
					#self.display(outfile)

		return (split_count, merger_count)

 
#----------------------------------------------------------#
	# added July 7 2013 jag
	def TestUnbrokenWord(self,morphemes,totalmorphemecount):
		# Check only unanalyzed words:  consider all cuts and select the best one, if it is an improvement.
		# THIS WAS NOT WORKING. NEEDED LIST OF BREAKS TO CONTAIN 0 AND len(self.word).
		#print "Are there considered to be breaks? len(self.breaks) = ", len(self.breaks)   #audrey  2015_12_02

		if len(self.breaks) > 0:
			return
		#bestscore = 0       
		#currentscore = 0
		bestlocation = 0
		this_word = self.word
		
		#ADDED    audrey    2015_12_02
		print "\npoint = 0 (i.e., unbroken word)"
		test_parse = class_word(this_word)
		test_parse.breaks = [0, len(this_word)]
		test_parse.EvaluateWordParse(morphemes,totalmorphemecount)
		bestscore = test_parse.TotalCost
		test_parse.displaytoscreen()
		
		for point in range(1,len(this_word)):
			print "\npoint =", point
			test_parse = class_word(this_word)	
			test_parse.breaks = [0, len(this_word)]     # ADDED  2015_12_02    audrey
			
			test_parse.addcut(point)
			test_parse.EvaluateWordParse(morphemes,totalmorphemecount)
			if bestscore == 0:
				bestscore = test_parse.TotalCost
			elif bestscore > test_parse.TotalCost:
				bestscore = test_parse.TotalCost 
				bestlocation = point
			test_parse.displaytoscreen()
			
		if bestscore > 0:
			#self.displaytoscreen()  #This is just all zeroes since the list of breaks is empty   audrey
			print "\nBest score = ", bestscore, "at point = ", bestlocation, "\n"    # FORMAT bestscore AS %8.1f
			
## ---------------------------------------------------------------------------------------##
##		End of class class_word:
## ---------------------------------------------------------------------------------------##

def PrintTopMorphemes(WordObjectList, outfile,threshold):
	print >>outfile, "\n\nDictionary:"
	morphemes = {}
	for word in WordObjectList: 	
		for n in range(1,len(word.breaks)):		 
			piece = word.getpiece(n)	 		
			IncrementCount(piece, morphemes)
 
	pieces = sorted (morphemes, key = morphemes.get, reverse = True  ) # sort by value

	for n in range(len(morphemes)):	
		morph = pieces[n]
		if morphemes[morph] <= threshold:
			break
		print >>outfile, n, morph , morphemes[morph]
#		if not morph in BestMorphemes:
#			BestMorphemes[morph] = []
#		BestMorphemes[morph].append((loopno, morphemes[morph] ))

#	for morph in BestMorphemes.keys():
#		print >>outfile, morph, BestMorphemes[morph]

 

#----------------------------------------------------------#
def PrintAllWords (wordclasslist, myoutfile,label):

	print >>myoutfile, "----------------------------------------\n"
	print >>myoutfile, "Word List:", label , "\n",
	print >>myoutfile, "----------------------------------------\n"

	#for word in wordclasslist:
		#word.display(myoutfile)

	for wordno in range(len(WordObjectList)):
		if wordno < 10 or wordno > 51735:     # there are 51753 lines
			WordObjectList[wordno].display(myoutfile)

#----------------------------------------------------------#
def PrintAllWords_textonly (wordclasslist, myoutfile,label):

	print >>myoutfile, "----------------------------------------\n"
	print >>myoutfile, "Word List:", label , "\n",
	print >>myoutfile, "----------------------------------------\n"

	for word in wordclasslist:
		word.displaytextonly(myoutfile)


#----------------------------------------------------------#
# returns the position of point in sorted list numberlist, returns -1 if point is not in numberlist
def positionInBreaks(point, numberlist):	 
	for n in range(0,len(numberlist)):
		if numberlist[n] == point:
			#print "position found: ", n
			return n
		if numberlist[n] > point:
			return -1
	return -1
#----------------------------------------------------------#
# returns index in sorted numberlist of "least upper bound" of point--that is, returns index of first entry which is >= point
# returns -1 if point exceeds all entries
def covering_index(point, numberlist):	 
	for n in range(0,len(numberlist)):
		if numberlist[n] == point:
			#print "position found: ", n
			return n
		if numberlist[n] > point:
			return n
	return -1   #should never happen!          
#----------------------------------------------------------#
# adds integer point to numberlist, keeping list sorted, returns the index it inserted it at
def AddIntegerToList(point, numberlist):		#expects that point is less than the last number in numberlist
	if len(numberlist) == 0:
		numberlist.append(point)
	for n in range(0,len(numberlist)):		
		if numberlist[n] > point:
			numberlist.insert(n,point)
			return n
	return -1
#----------------------------------------------------------#
def GetPiece(piecenumber, word, numberlist):
	return word[numberlist[piecenumber-1]: numberlist[piecenumber]]
#----------------------------------------------------------#
def GetPlog(morpheme, morphemes, totalmorphemecount):
#	if morpheme in morphemes:
#		thiscount = morphemes[morpheme]
#	else:
#		thiscount = 1
	thiscount = GetCount(morpheme, morphemes)	
	return math.log( totalmorphemecount / float( thiscount ) , 2 )
#----------------------------------------------------------#
def RecountMorphemes(WordObjectList):   #was (WordObjectList, morphemes)       audrey  2015_12_17
	newmorphemes = {}
	for word in WordObjectList:		 
		for n in range(1, len(word.breaks)):	#was range(len(word.breaks))   audrey  2015_12_17		 
			#piece = word[ breaks[word][n-1]:breaks[word][n] ]
			piece = word.getpiece(n)
			#IncrementCountAmount(piece,newmorphemes,len(piece))
			IncrementCount(piece,newmorphemes)
	return newmorphemes
		
#----------------------------------------------------------#
def ComputeTotalMorphemeCount(morphemes):
	totalmorphemecount = 0
	for item in morphemes:
		totalmorphemecount += float(morphemes[item]) # why float? is it because needed for division in plog?
	return totalmorphemecount


#----------------------------------------------------------#
def GetCount(item, dictionary):
	defaultcount = 0.5   #0.25  # 0.25 # 1
	if not item in dictionary:
		return defaultcount
	else:
		return dictionary[item]
#----------------------------------------------------------#
def IncrementCount(item, dictionary):    
	if not item in dictionary:
		dictionary[item] = 1
	else:
		dictionary[item] += 1
#----------------------------------------------------------#
def GetSegmentCost(morph, morphemes, totalmorphemecount):
	#PlogPiece = 10 * GetPlog(morph, morphemes, totalmorphemecount)  # Why 10?  Try it without.  audrey  2015_12_02  
	data_cost = plogcoeff * GetPlog(morph, morphemes, totalmorphemecount)          # factor was 10 in original code   audrey 2015_12_12
	dictionary_phonological_cost = len(morph) * float(BitsPerLetter)
	dictionary_order_cost = math.log (math.factorial(len(morph)), 2)      # shared cost - Try it!  audrey  2015_12_11
	dictionary_list_cost = 1.0    # audrey   WHY?
	
	segment_cost = data_cost + (dictionary_phonological_cost + dictionary_order_cost + dictionary_list_cost)/GetCount(morph, morphemes)
	return segment_cost
#----------------------------------------------------------#
def IncrementCountAmount(item, dictionary, amount):
	if not item in dictionary:
		dictionary[item] = amount
	else:
		dictionary[item] += amount
#----------------------------------------------------------#
  
#----------------------------------------------------------#

def ConsolePrint (word):
  print word,
  if word not in breaks:
    "Word not found." 
    return
  for n in breaks[word]:		
	if n==0:
		previous = n
		continue		 
	print word[ previous: n ],
	previous = n
  print





#----------------------------------------------------------#
# this is not currently being used: 
#----------------------------------------------------------#

def ShiftBreak (word, thiswordbreaks, shiftamount, outfile, totalmorphemecount):
	ShiftFormatString1 = "\nShifting.   %20s %35s %12s %12s %12s  %12s -    Old score %7.1f newscore: %5.1f " 
	ShiftFormatString2 = "                                                                      plog: %5.1f        %5.1f        %5.1f	    %5.1f" 
	ShiftFormatString3 = "                                                             log factorial: %5.1f        %5.1f        %5.1f         %5.1f" 
	splitword = []
	newwordbreaks = []
	start = 0
	
	#if there are any breaks in middle of word, pick a break point and shift it.
	if shiftamount > 0:
		if len(thiswordbreaks) <= 2:
			return (False, thiswordbreaks)
		else:
			breakindex = random.randrange(1, len(thiswordbreaks)-1)
		if thiswordbreaks[breakindex + 1] <= thiswordbreaks[breakindex] + shiftamount:	# this means the next breakpoint is too close to consider this shift
			return (False, thiswordbreaks);
	if shiftamount < 0:
		if len(thiswordbreaks) <= 2:
			return (False, thiswordbreaks)
		else:
			breakindex = random.randrange(1, len(thiswordbreaks)-1)
		if thiswordbreaks[breakindex - 1] >= thiswordbreaks[breakindex] + shiftamount:	# this means the next breakpoint is too close to consider this shift
			return (False, thiswordbreaks);

	for n in range(1, len(thiswordbreaks) ):				#breaks is a list of integers indicating morpheme breaks
		splitword.append( word[start: word.breaks[n] ] )	# splitword is a list of the morphemes
		start = thiswordbreaks[n]	 
	# info about old pieces
 	OldLeftPiece  			= GetPiece( breakindex, word, thiswordbreaks )
	OldRightPiece 			= GetPiece( breakindex+1, word,  thiswordbreaks )
	count1 				= GetCount(OldLeftPiece,morphemes)
	phonologicalcostOldLeftPiece 	= BitsPerLetter * len(OldLeftPiece) / float(count1)
	logfacOldLeftPiece 		= math.log( math.factorial( len(OldLeftPiece) ) , 2 )				
	count2 				= GetCount (OldRightPiece, morphemes)
	phonologicalcostOldRightPiece 	= BitsPerLetter * len(OldRightPiece) / float(count2)
	logfacOldRightPiece		= math.log( math.factorial( len(OldRightPiece) ) , 2 )	
	oldplogLeft 			= GetPlog ( OldLeftPiece, morphemes, totalmorphemecount)
	oldplogRight 			= GetPlog ( OldRightPiece, morphemes, totalmorphemecount)
	oldscore   			= oldplogLeft + oldplogRight + logfacOldLeftPiece  + logfacOldRightPiece +    phonologicalcostOldLeftPiece + phonologicalcostOldRightPiece

	# info about new pieces
	newwordbreaks 			= thiswordbreaks[:]
	newwordbreaks[breakindex]	+= shiftamount

	NewLeftPiece   			= GetPiece( breakindex, word, newwordbreaks )
	count1 				= GetCount (NewLeftPiece, morphemes)	
	phonologicalcostNewLeftPiece 	= BitsPerLetter * len(NewLeftPiece) / float(count1)
	logfacNewLeftPiece 		= math.log(math.factorial( len(NewLeftPiece) ) , 2 )	

	NewRightPiece   		= GetPiece (breakindex + 1, word, newwordbreaks) 
	count2 				= GetCount (NewRightPiece, morphemes)
	phonologicalcostNewRightPiece 	= BitsPerLetter * len(NewRightPiece) / float(count2)
	logfacNewRightPiece 		= math.log(math.factorial( len(NewRightPiece) ) , 2 )	
 
	newplogLeft 			= GetPlog(NewLeftPiece, morphemes,totalmorphemecount)
	newplogRight 			= GetPlog(NewRightPiece, morphemes,totalmorphemecount)
	newscore   			= newplogLeft + newplogRight +  logfacNewLeftPiece + logfacNewRightPiece    + phonologicalcostNewLeftPiece + phonologicalcostNewRightPiece

 	start = 0
	newsplitword = []
	for n in range(1, len(newwordbreaks) ):				#breaks[word] is a list of integers indicating morpheme breaks
		newsplitword.append( word[start: newwordbreaks[n] ] )	# splitword is a list of the morphemes
		start = newwordbreaks[n]

	if newscore < oldscore:
		if False:
			print "shifting " + ' '.join(splitword) + ' to ' + ' '.join(newsplitword)
			shift_counter.append(1)
			print ShiftFormatString1 % (word, splitword, OldLeftPiece, OldRightPiece, NewLeftPiece, NewRightPiece, oldscore, newscore )	
			print ShiftFormatString2 %(  oldplogLeft , oldplogRight, newplogLeft, newplogRight) 		 				 
			print ShiftFormatString3 %(  logfacOldLeftPiece , logfacOldRightPiece, logfacNewLeftPiece, logfacNewRightPiece) 
		return (True, newwordbreaks )
	return (False, thiswordbreaks)	









 
#------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------#









#--------------------------------------------------------------------##
#		Main program 
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
	print sys.argv[1]
	infilename = sys.argv[1] 
if not os.path.isfile(infilename):
	print "Warning: ", infilename, " does not exist."
if g_encoding == "utf8":
	infile = codecs.open(infilename, encoding = 'utf-8')
else:
	infile = open(infilename) 

print "Data file: ", infilename

# organize files like this or change the paths here for output
outfolder = '../data/'+ language + '/gibbs_wordbreaking/'
outfilename = outfolder +  "gibbs_pieces.txt"
outfilename1 = outfolder +  "word_list.txt"
outfilename2 = outfolder +  "split_merge_counts.txt"
if g_encoding == "utf8":
	outfile = codecs.open(outfilename, encoding =  "utf-8", mode = 'w',)
	outfile1 = codecs.open(outfilename1, encoding =  "utf-8", mode = 'w',)
	outfile2 = codecs.open(outfilename2, encoding =  "utf-8", mode = 'w',)
	print "yes utf8"
else:
	outfile = open(outfilename,mode='w') 
	outfile1 = open(outfilename1,mode='w') 
 	outfile2 = open(outfilename2,mode='w') 

#------------------------------------#

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

wordlist = infile.readlines()    #  This is a list  audrey   2015_12_04
print "length of wordlist: ", len(wordlist)

#---------------------------------------------------------#
#	End of file input, output
#---------------------------------------------------------#







#---------------------------------------------------------#
#	2. Random splitting of words
#---------------------------------------------------------#
 
breakprob = 0.2   #0.5  #0.4 #0.3  #0.2    # 0.1   # where does this probability come from? is it a statistic about languages in general/English?
#breaks = {}   # a dictionary of words mapped to a list of indices where the breaks are
totalmorphemecount = 0  # number of morphemes, counting duplicates
WordObjectList = [] # this is a list of objects of class class_word



for word in wordlist:	
	 
	this_word = class_word(word)	
	start = 0		 
	this_word.breaks.append(0)                     # always put a break at the beginning
	for n in range(1, len(word)):              # won't randomly put a break at the beginning or end
		if (random.random() < breakprob):                #   or (n - start >= 10):  (i.e., limit length)  # about every 10 letters add a break
			piece = word[start:n]				 
			this_word.breaks.append( n )
			start = n	
			IncrementCount(piece,morphemes)  # increment piece in global morphemes dictionary
			totalmorphemecount += 1 #len(piece)		 
	if start < len(word)  :                    # should always be true...
		piece = word[start:]
		this_word.breaks.append( len(word) )   # always put a break at the end
		IncrementCount(piece,morphemes)
	 	totalmorphemecount += 1 #len(piece)

	 
 	WordObjectList.append(this_word)
		
for word in WordObjectList:
	word.EvaluateWordParse(morphemes, totalmorphemecount)


pieces = sorted (morphemes, key = morphemes.get, reverse = True  ) # sort by value   # NOT USED  2015_12_16  audrey
#for piece in pieces:
#	if morphemes[piece] < 5:    # only add to dictionary if morpheme occurred 5+ times
#		continue	
#	print >>outfile, piece, morphemes[piece]    # MAY DECIDE TO PRINT THIS   audrey  2015_12_04

print "End of initial randomization." 






#----------------------------------------------------------#
#		3. Main loop
#----------------#----------------------------------------------------------#------------------------------------------#
NumberOfIterations = 10       # 20  # 20000  # 160			# 200 seems to be a good number
print "Number of iterations: ", NumberOfIterations
#BestMorphemes = {}          	# a dictionary of morphemes mapped to a list of (loop number, occurence count) pairs that are the best at that loop
#logflag = False
LoopNumberAtWhichWeStartTracking = 20
for loopno in range (NumberOfIterations):
	#print >>outfile, "loop number", loopno  #loopno is shown along with split_count and merger_count
	#print loopno   #loopno is shown along with split_count and merger_count   
	split_count = 0
	merger_count = 0
	#shift_count = 0

	for wordno in range(len(WordObjectList)):
	#for wordno in range(10):
		this_word = WordObjectList[wordno]
		(split_count, merger_count) = this_word.CompareAltParse2(split_count, merger_count)

		 
 
#	if split_count + merger_count + shift_count > 1:    # Note that these counts are not maintained    audrey  2015_12_03
#		# prints to both output file and stdout
#		print >>outfile, loopno , "Splits during this loop:", split_count, "Merges: ", merger_count,  "Shifts: ", shift_count
#		#print loopno, "Splits during this loop:", split_count, "Merges: ", merger_count, "Shifts: ", shift_count

	if split_count + merger_count > 0:    # Note that these counts are not maintained    audrey  2015_12_03
		# prints to both output file and stdout
		print >>outfile2, "%4s" %loopno, " ", split_count, merger_count
		print "%4s" %loopno, " ", split_count, merger_count

	# recalculate morpheme frequencies & number of morphemes
	#morphemes = RecountMorphemes(WordObjectList,morphemes)	 
	morphemes = RecountMorphemes(WordObjectList)	 
	totalmorphemecount = ComputeTotalMorphemeCount(morphemes)

################  NOTE THAT THIS UPDATE OF EVERYTHING IS COMMENTED OUT FOR EXPERIMENT  #################################	
#	for wordno in range(len(WordObjectList)):  
#		wordstring = WordObjectList[wordno].word
#		this_word = class_word(wordstring)    # audrey  2015_12_10  constructor instead of reinit in EvaluateWordf
#		this_word.partialcopy(WordObjectList[wordno])
#		this_word.EvaluateWordParse(morphemes,totalmorphemecount)
		
#		WordObjectList[wordno] = this_word    # audrey  QuickFix  2015_12_10
		
	
	#----------------------------------------------------------#
	#       output intermediate results 			   #	
	#----------------------------------------------------------#
	# prints out the 100 top morphemes initially, after 10 loops, after 100, and after 200
	#if loopno == 0  or  loopno == 10 or loopno == 20 or  loopno == 100 or loopno == NumberOfIterations -1:
	if loopno == NumberOfIterations -1:

 		# COMPUTES COSTS USING FINAL COUNTS. DOES NOT CHANGE PARSE.	
		for wordno in range(len(WordObjectList)):  
			wordstring = WordObjectList[wordno].word
			this_word = class_word(wordstring)    # audrey  2015_12_10  constructor instead of reinit in EvaluateWordf
			this_word.partialcopy(WordObjectList[wordno])
			this_word.EvaluateWordParse(morphemes,totalmorphemecount)		
			WordObjectList[wordno] = this_word    # audrey  QuickFix  2015_12_10

#		for each_word in WordObjectList:
#			each_word.EvaluateWordParse(morphemes,totalmorphemecount)	
 
		# first: print ALL words, with their analysis.
 		#print >>outfile, "----------------------------------------\nLoop number:", loopno, "\n"
 		print >>outfile1, "----------------------------------------\nLoop number:", loopno, "\n"
		#PrintAllWords(WordObjectList,outfile1,loopno)
		PrintAllWords_textonly(WordObjectList,outfile1,loopno)     # makes it easier to see parse diffs   audrey  2015_12_21
		threshold = 0
		print >>outfile, "----------------------------------------\nLoop number:", loopno, "\n"
		PrintTopMorphemes(WordObjectList, outfile,threshold)   #audrey  2015_12_09  Temporarily removed for BBEdit memory reasons
		#pieces = sorted (morphemes, key = morphemes.get, reverse = True  ) # sort by value
		
		# prints out the 100 top morphemes
		#for n in range (100):	
		#	morph = pieces[n]
		#	print >>outfile, n, morph , morphemes[morph]
		#	if not morph in BestMorphemes:
		#		BestMorphemes[morph] = []
		#	BestMorphemes[morph].append((loopno, morphemes[morph] ))

#for morph in BestMorphemes.keys():
#	print >>outfile, morph, BestMorphemes[morph]

# MOVED UPWARD SO THAT PERSON DOING INTERACTIVE QUERIES CAN VIEW THE INFORMATION DERIVED BY PROGRAM
outfile2.close()
outfile1.close()
outfile.close() 


CommandList=list()








while (True):
  command = raw_input("Enter word:")
  CommandList.append(command)
  #command_words = command.split()
  if len(command)==0:
	print "enter a word."
	continue

  if command =="exit"  :
    break
  #ConsolePrint(command)
  object_word = class_word(command)
  object_word.TestUnbrokenWord(morphemes, totalmorphemecount)

















 #----------------------------------------------------------#
 #	4. Print results
 #----------------------------------------------------------#

#MinimumOccurrenceCount = 3   # if there are less than 3 occurrences of a morpheme, it probably doesn't mean much
#PrintTopMorphemes(WordObjectList, outfile, MinimumOccurrenceCount)
#PrintAllWords(WordObjectList, outfile1, "Final")

# MOVED UPWARD
#outfile1.close()
#outfile.close() 

