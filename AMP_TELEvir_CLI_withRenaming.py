import os 
import gzip
import time
from sys import exit  
import shutil
from tkinter import *
from tkinter import filedialog 
from tkinter.filedialog import askdirectory
from Bio import SeqIO
import numpy as np 
from numpy import mean
import matplotlib.pyplot as plt
import datetime 
import argparse


PARSER = argparse.ArgumentParser(description = """
COMMAND LINE TOOL FOR AUTOMATING MULTI-FILE PROCESSING OF MINION NGS DATA  
AUTHOR: RICARDO JORGE PAIS @ INSA    
DATE OF LAST UPDATE: 14/4/2021

DESCRIPTION:
The Script performs an fully automated data processing of multiple fastq files generated by miniON (OXFORD NANOPORE TECKNOLOGIES)
using a medaka network model that generates preliminary variants which is further refined down the pipeline.

The tool requires the following mandatory inputs  :
	* -g  < the reference genome sequence path (must be in fasta format) >  
	* -s  < the folder path where with the reads files are located (must be in fastq format) > 
	* -i  < the path for the metadata file (*.tsv or *.csv ) containing samples ID and file names >
    
As OUTPUTS, the script generates the following files organized in sample folders inside a Results folder:
    *  Predicted consensus file with sample ID (consensus.fasta)
    *  Bam files
    *  Sample coverage file (depth.gz)
    *  Curated variants file (medaka_variants.vcf) with detail information on each detected variant   
    *  Sample Coverage quality plot with variants location in the sequence locus 
    *  Basic stats reports of the sample
    *  Overal analysis reports in csv files, one with the list of all mutations detected and another with main stats"
    *  Run report contaning pipeline parameters and other info  

Optionally, you can get the paths using the choose GUI option by typing "choose" after each mandatory input command.
Example:  -g choose -s choose -i choose.
You can also set most pipeline parameters for tuning the analysis by adding adicional arguments.
If not defaut settings will be applied.


""",  formatter_class= argparse.RawDescriptionHelpFormatter  ) 

PARSER.add_argument( "--refgenome", "-g", help= "The path for the fasta file with the reference genome\n", required = True, dest = "REFGENOME", action = "store"  ) 
PARSER.add_argument( "--samples", "-s", help= "The path for the folder where the sample reads are located\n", required = True, dest = "PATH", action = "store"  ) 
PARSER.add_argument( "--metadata", "-i", help= "The path for the file with files names and associated metadata\n", required = True, dest = "META", action = "store"  ) 
PARSER.add_argument( "--version", "-v", action="version", version = "Alpha version 0.1 (April 2021) >>>> Ricardo J. Pais <<<< " ) 
PARSER.add_argument( "--run_name", "-a", help= "Name of the folder containing the output results of the analysis (Default is set as miniON_Results)\n", type = str, required = False, dest = "RUN_NAME", action = "store", default="miniON_Results" ) 
PARSER.add_argument( "--model_medaka", "-m", help= "Name of the medaka model available in medaka framework version 1.2 ( default = r941_min_high_g360)\n", type = str, required = False, dest = "MODEL", action = "store", default= "r941_min_high_g360" ) 
PARSER.add_argument( "--cutoff1", "-c", help= "Sample coverage cutoff for masking variants and consensus ( default = 30)\n", type = int, required = False, dest = "CUTOFF1", action = "store", default= 30  ) 
PARSER.add_argument( "--Ideal_coverage", "-b", help= "Ideal sample coverage for considering very high coverage ( default = 200). Note that cannot be lower than defined cutoff\n", type = int, required = False, dest = "IDEAL_COVERAGE", action = "store", default= 200 ) 
PARSER.add_argument( "--minQ_Reads", "-q", help = "Cutoff for defining the minimum quality of reads to be filtered (q = -10 log[base error], default = 10, 0 ignores filter )\n", type = int, required = False, dest = "MINQREADS", action = "store", default= 10 ) 
PARSER.add_argument( "--headcrop", "-e", help= "Length of inicial read sequence to crop (default = 70 )\n", type = int, required = False, dest = "HEADCROP", action = "store", default= 70 ) 
PARSER.add_argument( "--tailcrop", "-t", help= "Length of final read sequence to crop (default = 70 )\n", type = int, required = False, dest = "TAILCROP", action = "store", default= 70 ) 
PARSER.add_argument( "--minRlength", "-l", help= "Minimum length of the sequence for considering the read after cropping (default = 50 )\n", type = int, required = False, dest = "MINRLENGHT", action = "store", default= 50 ) 
PARSER.add_argument( "--minFrequency", "-f", help= "Minimum base frequency threshold for considering a putative variants (default = 0.8 )\n", type = float, required = False, dest = "MINFREQ", action = "store", default= 0.8 ) 
PARSER.add_argument( "--maxINDEL", "-d", help= "Maximum number of insertions and deletions allowed to be consider true, higher numbers are considered as gaps and ignored\n", type = int, required = False, dest = "MAXINDEL", action = "store", default= 10*9) 
PARSER.add_argument( "--Ignore_Regions", "-u", help= "Input specific regions for ignoring across the sequence. This will mask and ignore variants on these regions. Not working in this version.\n Example for ignoring first 100 bases on locus 1,2 and 3 ...  -u 1:10-100;2:1-100;3:1-100\n", type = str, required = False, dest = "IGNORE_REGIONS", action = "store", default = "none" ) 
PARSER.add_argument( "--minReads", "-n", help= "Miminum number of reads for processing data and generating results (default = 100)\n", type = int, required = False, dest = "MINREADSN", action = "store", default= 100 ) 
PARSER.add_argument( "--minSeqCov", "-p", help= "Miminum sequence coverage (in percentage) to consider results robust  (default = 70)\n", type = int, required = False, dest = "MINSEQCOV", action = "store", default= 70 ) 
ARGS = PARSER.parse_args() 


def Get_Sample_IDname (filepath):
	name = filepath.split(".")[0].split("/")[-1]
	return name


def Medaka_consensus_prediction(samplepath ,refpath, model, Output_path):
	I, M, R  = samplepath , model, refpath
	O = Output_path  # output folder
	output_exists = os.path.isdir(O)
	if output_exists == True:
		shutil.rmtree(O)
	if M == "default":
 		commands =  "medaka_consensus -i "+ I +" -d "+ R +  " -o " + O
	else:
 		commands =  "medaka_consensus -i "+ I +" -d "+ R +  " -o " + O + " -t 8  -m " + M 
	os.system(commands)
	exist_status = os.system(commands)
	if (exist_status != 0):
		print('Fail to run medaka consensus tool commands\n please ensure medaka is installed and run again the pipeline')
		exit(0)
	bamFile = O + "/calls_to_draft.bam" 
	ProbsFile = O + "/consensus_probs.hdf"
	Consensus = O + "/consensus.fasta"
	return [bamFile, ProbsFile, Consensus ]


def CoverageExtraction(bam): 
	Output_file = bam.split("calls_to_draft")[0] + "reads_coverage.depth"
	commands =  "samtools depth -aa -d0 " + bam + " > " + Output_file 
	os.system(commands)
	exist_status = os.system(commands)
	if (exist_status != 0):
		print('Fail to run samtools commands\n please ensure that the tool is installed and run again the pipeline')
		exit(0)		
	return Output_file


def GunZip_Files ( FILES ):
	for Output_file in FILES:
		with open(Output_file, "rb") as initial:
			with gzip.open(Output_file + ".gz", "wb" ) as zipped:  
				zipped.writelines(initial)


def VariantCalling_Medaka(probs, ref, Bam ): 
	Output_file = probs.split("consensus_probs")[0] + "medaka_variant.vcf"
	temp = probs.split("consensus_probs")[0] + "temporary.vcf"
	commands =  "medaka variant --verbose " + ref + " " + probs + " " +  temp
	os.system(commands)
	exist_status = os.system(commands)
	if (exist_status != 0):
		print('Fail to run medaka variant call commands\n please ensure that the tool is installed and run again the pipeline')
		exit(0)
	commands =  "medaka tools annotate  " + temp + " " + ref + " " + Bam + " " + Output_file
	os.system(commands)
	exist_status = os.system(commands)
	if (exist_status != 0):
		print('Fail to run annotated tools commands\n please ensure that the tool is installed and run again the pipeline')
		exit(0)
	return Output_file


def Add_SampleIDinfo_fasta(fastafile, info, locusList ):
	newfasta = ""
	fasta = open (fastafile, "r")
	seqN = 0
	for line in fasta:
		if line[0] == ">":
			newfasta = newfasta + "> " +  locusList[seqN] + " " + info + "\n"
			seqN = seqN + 1
		else:
			newfasta = newfasta + line	
	fasta.close()
	New = open(fastafile, "w" )
	New.write(newfasta)
	New.close()

def Get_Variant_INFO_fromVCF(VCFpath):
	POSITIONS, MUTATIONS, TYPE, SCORES, IDSEQ, COVERAGES = [ ], [ ],[ ] , [ ], [], []
	vcf_file = open( VCFpath, "r" )
	for line in vcf_file:
		if line[0] != "#":
			mutType = "Other"
			A = line.split("\t")[4]
			R = line.split("\t")[3]
			SRinfo = line.split("\t")[7].split("SR=")[1].split(";")[0].split(",")
			ARinfo = line.split("\t")[7].split("AR=")[1].split(";")[0].split(",")
			SR = float(SRinfo[2]) + float(SRinfo[3]) 
			AR = sum([float(AR) for AR in ARinfo ])
			DPSP = float(line.split("\t")[7].split("DPSP=")[1].split(";")[0])
			DP = float(line.split("\t")[7].split("DP=")[1].split(";")[0])
			IDseq = line.split("\t")[0] 
			if (DPSP - AR) > 0:
				FREQ = round(SR /(DPSP - AR), 3)
			else:
				FREQ = 0
			if len(A) == 1 and len(R) == 1:
				mutType = "SNP"
			if len(A) > len(R):
				mutType = "Insertion"
			if len(R) > len(A):
				mutType = "Deletion"
			POSITIONS.append(line.split("\t")[1])
			MUTATIONS.append(R + "-->" + A)
			TYPE.append(mutType)
			SCORES.append( str(FREQ))
			IDSEQ.append(IDseq)
			COVERAGES.append(DP)
	vcf_file.close() 
	return [POSITIONS, MUTATIONS, SCORES, TYPE, IDSEQ, COVERAGES ]


def Refine_medaka_VCF_with_coverage_and_frequency ( VCFpath, cutoff, BadRegions, MinFreq, INDELmax ): 
	VCF2, n , id_count, IDj = "", 0, 0, "inicial" 
	VCF_file = open( VCFpath, "r" )
	for line in VCF_file:
		if line[0] == "#":
			VCF2 = VCF2 + line 
		if line[0] != "#": 
			# position of variant in sequence as a string tag for serching possible tags in bad regions list     			
			Pi = line.split("\t")[0] + "_" + line.split("\t")[1]  
			# get coverage and frequency values  
			IDi = line.split("\t")[0]
			if IDi != IDj:
				id_count = id_count + 1
				IDi = IDj 
			SRinfo = line.split("\t")[7].split("SR=")[1].split(";")[0].split(",")
			ARinfo = line.split("\t")[7].split("AR=")[1].split(";")[0].split(",")
			SR = float(SRinfo[2]) + float(SRinfo[3]) 
			AR = sum([float(AR) for AR in ARinfo ])
			DPSP = float(line.split("\t")[7].split("DPSP=")[1].split(";")[0])
			DP = float(line.split("\t")[7].split("DP=")[1].split(";")[0])
			seqTag = str(id_count) + "_" + str(DP)
			if (DPSP - AR) > 0:
				FREQ = round(SR /(DPSP - AR), 3)
			else:
				FREQ = 0
			# compute the number of bases that are on delected or inserted ( aims removing possible error variants )
			MLVAR = abs(len(line.split("\t")[4]) - len(line.split("\t")[3]))
			if DP >= cutoff and seqTag not in BadRegions and FREQ >=MinFreq  and MLVAR <= INDELmax:
				VCF2 = VCF2 + line 
			n=n+1		
	VCF_file.close()
	VCF_file2 = open(VCFpath, "w" )
	VCF_file2.write(VCF2)
	VCF_file2.close()


def UnecessaryFiles_remove(Gpath, Spath, output_path, TemporarySTATS, Q):
	os.remove(TemporarySTATS)
	Extensions = [".mmi", ".fai" ]
	for extension in Extensions:
		os.remove(Gpath+extension)
	if Q > 0:
		HQfilepath = Spath.split(".")[0] + "_HQ.fastq.gz"
		os.remove(HQfilepath)
	files = os.listdir(output_path)
	for File in files:
		if File.split(".")[-1] == "depth" or File.split(".")[-1] == "hdf" or File.split(".")[0] == "temporary" or File.split(".")[0] == "allinment" :
			os.remove(output_path+"/"+File) 

def HQfilterReads(path, Q, H, T, L ):
	Output_file = path.split(".")[0] + "_HQ.fastq.gz"
	param = 	"-q " + str(Q) +  " -l " + str(L) +  " --headcrop " + str(H) + " --tailcrop " + str(T)
	commands =  "gunzip -c " + path + " | NanoFilt " + param +  " | gzip > " + Output_file
	print ("\n ...filtering reads with quality > Q", str(Q), " \n ")
	os.system(commands)
	exist_status = os.system(commands)
	if (exist_status != 0):
		print('Fail to run NanoFilt tool commands for HQ reads filtering \n please ensure that the tool is installed and run again the pipeline')
		exit(0)		 
	return Output_file

def Reads_Stats(ReadsPath, PATH, NAME ):
	Output_file =  PATH + "/" + NAME + ".txt"
	commands =  "NanoStat --fastq "  + ReadsPath +  "  --tsv > " + Output_file
	os.system(commands)
	exist_status = os.system(commands)
	if (exist_status != 0):
		print('Fail to run NanoStats tool commands\n please ensure that the tool is installed and run again the pipeline')
		exit(0)
	MeanReadLength, ReadLengthSTD, MeanReadQual, NumberReads, TotalBases =  "", "", "", "", ""   
	SF = open(Output_file)
	for line in SF:
		S = line.split("\t")
		if S[0] == "mean_read_length":
			MeanReadLength=S[1]
		if S[0] == "read_length_stdev":
			ReadLengthSTD=S[1]
		if S[0] == "mean_qual":
			MeanReadQual=S[1]
		if S[0] == "number_of_reads":
			NumberReads=S[1]
		if S[0] == "number_of_bases":
			TotalBases=S[1]
	SF.close()
	return [MeanReadLength, ReadLengthSTD, MeanReadQual, NumberReads, TotalBases]


def import_seqs(fasta_file):
	seqs = []
	nuc_to_NUC = {"a": "A","c":"C", "t":"T", "g":"G"}  
	for record in SeqIO.parse(fasta_file, 'fasta'):
		seqid = record.id
		sequence = str(record.seq)
		sequence_new = ""
		for nuc in sequence:
			if nuc in ["a", "c", "t", "g" ]:
				sequence_new = sequence_new + str(nuc_to_NUC.get(nuc)) 
			else:
				sequence_new = sequence_new + str(nuc)

		seqs.append([seqid, sequence_new])	 
	return seqs


def LowCov_SeqMasker(AlignSequences, depthFilePath , output_fasta, cutoff, Bad_regions) :
	seqHeader, n, depths, Ncount, missmatch = [], 0, [], 0, 0
	Depth_File = open(depthFilePath, "r") 
	for line in Depth_File:
		n= n+1
		info = line.split("\t")
		value = int(float(info[2]))
		if info[0] not in seqHeader:
			seqHeader.append(info[0]) 
			if n !=1:
				depths.append(values)
			values = [ value ]
		else:
			values.append(value)
	depths.append(values)
	Depth_File.close() 
	RefSeq, SampleSeq, SeqID = [], [], [] 
	for seq in AlignSequences:
		if seq[0].find("Reference") > -1:
			RefSeq.append(seq[1])
		if seq[0].find("Sample") > -1:
			SampleSeq.append(seq[1])
			SeqID.append(seq[0])
	sequences_masked = [ ]
	SeqLenght = 0 
	for i, seq in enumerate(RefSeq):
		seq2 = ""
		k = 0 
		for j, rB in enumerate(seq):
			icov = float(depths[i][k])
			sB =""
			if j < len (SampleSeq[i]):
				sB = SampleSeq[i][j]   
			if rB != "-":
				if k < len(depths[i]) -1 :    
					k = k + 1
				if sB != "-":
					SeqLenght = SeqLenght+1
					if icov < cutoff or SeqLenght in Bad_regions:
						sB = "N"
						Ncount = Ncount+1
					seq2 = seq2 + sB
			if rB == "-" and sB != "-":
				SeqLenght = SeqLenght + 1
				if SeqLenght in Bad_regions and icov < cutoff:
					sB = "N"
					Ncount = Ncount+1
				seq2 = seq2 + sB
				missmatch = missmatch + 1
			if rB != "-" and sB == "-":
				 missmatch = missmatch + 1
		seq2 = seq2.replace("\n", "" )  
		sequences_masked.append(seq2)
	File2 = open(output_fasta, 'w')
	for i, seq in enumerate(sequences_masked):
		File2.write( ">" + SeqID[i] + "\n" )
		File2.write(seq + "\n")
	File2.close() 
	return [Ncount, SeqLenght, round(Ncount/SeqLenght*100, 2 ), missmatch ] 



plt.style.use("ggplot")
plt.rcParams["figure.figsize"] = (20,10)
def CoverageQuality_Plot(tsh1, tsh2, DepthFilePath, mutationalINFO):
	Coverages_ALL, CoverageSeqs, PositionSeqs, IDSEQ, maxLen = [] ,[] ,[] ,[] , 0 
	F = open(DepthFilePath)
	for line in F:
		ID = line.split("\t")[0]
		C = int(float(line.split("\t")[2]))
		P = int(float(line.split("\t")[1]))
		if P > maxLen:
			maxLen = P 
		Coverages_ALL.append(C)
		if ID not in IDSEQ:
			if len(IDSEQ) != 0:
				CoverageSeqs.append(COVsi)
				PositionSeqs.append(POSsi)
			COVsi = [C]
			POSsi = [P] 
			IDSEQ.append(ID)
		else:	
			COVsi.append(C)
			POSsi.append(P)
	CoverageSeqs.append(COVsi)
	PositionSeqs.append(POSsi)
	F.close()
	variant_positions, variant_coverages, ids_variants = [], [] ,[] 
	for i, pos in enumerate(mutationalINFO[0]):
		if mutationalINFO[4][i] not in ids_variants:
			if len(ids_variants) != 0:
				variant_coverages.append(COVsi)
				variant_positions.append(POSsi)
			COVsi = [ mutationalINFO[5][i] ]
			POSsi = [pos] 
			ids_variants.append(mutationalINFO[4][i])
		else:	
			COVsi.append(mutationalINFO[5][i])
			POSsi.append(pos)
	variant_coverages.append(COVsi)
	variant_positions.append(POSsi)
	seq = [ i for i in range(1, maxLen) ] 
	plt.clf()
	plt.style.use("ggplot")
	plt.rcParams["figure.figsize"] = (20,10)
	plt.xlabel('Sequence position (bp)', size = 20)
	plt.ylabel(" Coverage ", size = 20)
	plt.tick_params(axis = "both", labelsize = 18)
	plt.title(" Coverage accross the sequence ", size =20)
	plt.yscale('log')
	plt.scatter( [], [], color = "green", label = "HQ",  s = 40   ) 
	plt.scatter( [], [] , color = "yellow", label = "OK Q",  s = 40   ) 
	plt.scatter( [] , [], color = "red", label = "LQ",  s = 60   )
	plt.plot( seq, [tsh2 for i in range(1, maxLen) ] , "g--", label = "HQ cutoff", linewidth = 3   )
	plt.plot( seq , [tsh1 for i in range(1, maxLen) ] , "r--", label = "LQ cutoff", linewidth = 3   )
	plt.plot( seq , [np.mean(Coverages_ALL) for i in range(1, maxLen) ], "k--", label = "Average coverage", linewidth = 3   ) 
	plt.scatter( [  ], [], label = "Variants " , color = "blue" ,  s = 200, marker = "+"  ) 
	for k in range(len(IDSEQ)):
		seq1, cov1 , seq2, cov2 ,seq3, cov3  = [],[],[],[],[],[]
		for i, cov in enumerate(CoverageSeqs[k]):
			if  cov <= tsh1:
				seq1.append( PositionSeqs[k][i])
				cov1.append(cov)
			if cov > tsh1 and cov < tsh2:
				seq2.append( PositionSeqs[k][i])
				cov2.append(cov)
			if cov >= tsh2:
				seq3.append(PositionSeqs[k][i])
				cov3.append(cov)
		plt.scatter( seq3, cov3, color = "green",  s = 40   ) 
		plt.scatter( seq2, cov2 , color = "yellow",  s = 40   ) 
		plt.scatter( seq1 , cov1, color = "red",  s = 60   )
	for k in range(len(variant_positions)):
		plt.scatter( [ float(P) for P in variant_positions[k] ], [float(C) for C in variant_coverages[k]], color = "blue"  ,  s = 200, marker = "+"  ) 
	plt.axis([0, maxLen, 0 , max(Coverages_ALL)*10 ])
	plt.legend(fontsize =18, loc = 'upper right', ncol=7 )
	PathToSave = DepthFilePath.split("reads")[0] 
	plt.savefig( PathToSave  + "coverageQualityPlot" )
	return Coverages_ALL


def Run_Alingment_MAFFT(RefSeq, ConsenSeq, path ): 
	ipath = path + "/temporary.fasta"
	ifile = open(ipath, "w")
	ifile.write(">Reference " + RefSeq[0]+ "\n")
	ifile.write(RefSeq[1]+ "\n") 
	ifile.write(">Sample " + ConsenSeq[0]+ "\n")
	ifile.write(ConsenSeq[1]+ "\n")
	ifile.close()
	output = path + "/allinment.fasta"
	commands =  "mafft --auto " + ipath + " > " + output 
	os.system(commands)
	exist_status = os.system(commands)
	if (exist_status != 0):
		print('Fail to run mafft tool commands for allinment fasta file generation...\n please ensure that the tool is installed and run again the pipeline')
		exit(0)
	return output


def Generate_Bad_regions_index ( intervals ):  
	IndexRemove = []
	if intervals.find("-") > 0  and intervals.find("1:"): 
		A = intervals.split(";")
		for region in A:
			interval = region.split(":")[1]
			Iid = region.split(":")[0]  
			vi = int(float(interval.split("-")[0]))
			vf = int(float(interval.split("-")[1]))
			AA = [ Iid + "_" +str(i) for i in range(vi,vf+1) ]
			for j in AA:
				if j not in IndexRemove:
					IndexRemove.append(j)
	return IndexRemove       


def WriteParametersReport ( path, Refpath, model, coverage_cutoff, minQReads, icut, fcut, cutRegions, analysisName, Ntotal, avTime, date  ):
    refname ="unknow reference"
    f1 = open(Refpath, "r" )
    for line in f1:
        if line[0] == ">" and len(line) > 3:
             refname = line[1:-1]
    f1.close()
    f2 =open(path + "/RunParameters.txt", "w")
    f2.write ("===============================================================================================================================\n")
    f2.write ("      Running information and parameters of the Automated pipeline for nanopore data processing (alpha version)                                \n")
    f2.write ("===============================================================================================================================\n")
    f2.write ( "\n   Analysis code name                      " +  analysisName  +  "\n")
    f2.write ( "\n   Analysis running date                   " +  str(date)   + "\n")
    f2.write ( "\n   Genome reference                        "  +  refname   + "\n")
    f2.write ( "\n   Medaka model used                       " +  model   + "\n")
    f2.write ( "\n   Minimum reads quality cutoff            "  +  str(minQReads)   + "\n")
    f2.write ( "\n   Coverage cutoff for masking             " +  str(coverage_cutoff)   + "\n")
    f2.write ( "\n   Base trimmning head crop on reads       " +  str(icut)   + "\n")
    f2.write ( "\n   Base trimmning tail crop on reads       " +  str(fcut)   + "\n")
    f2.write ( "\n   Other masking intervals                 " +  cutRegions   +  "\n")
    f2.write ( "\n   Number of files processed               " + str(Ntotal)   + "\n")
    f2.write ( "\n   Total processing time                   " +  str(round(avTime/60*Ntotal , 1 )) + " min  \n")
    f2.write ( "\n   Average processing time per sample      " + str(round(avTime/60 , 1 )) + " min \n")
    f2.write ("\n===============================================================================================================================\n")
    f2.close()


def VCF_TO_CONSENSUS_bcftools( VCFpath, ConsensusPath, ReferencePath, tempPath ):
	temporaryVCFgz = tempPath + "/temporary.vcf.gz"  
	command1 =  "bcftools convert -Oz -o " + temporaryVCFgz + " " + VCFpath
	os.system(command1)
	exist_status1 = os.system(command1)
	command2 =  "bcftools index -f " + temporaryVCFgz
	os.system(command2)
	exist_status2 = os.system(command2)
	command3 =  "bcftools consensus " + temporaryVCFgz + " -f " + ReferencePath + " o " + ConsensusPath
	os.system(command3)
	exist_status3 = os.system(command3) 
	if (exist_status1 != 0) or (exist_status2 != 0) or (exist_status3 != 0):
		print('Fail to run bcf tools for new consensus generation!\n please ensure that the tool is installed and run again')
		exit(0)


def BADsampleCheker( Spath, TempPath, H, T, L, minR ):
	DECISON = "reject"
	commands =  "NanoStat --fastq "  + Spath +  "  --tsv > " + TempPath 
	os.system(commands)
	MRL,  RLSTD, NTR =  0, 0, 0   
	SF = open(TempPath)
	for line in SF:
		S = line.split("\t")
		if S[0] == "mean_read_length":
			MRL = float(S[1])
		if S[0] == "read_length_stdev":
			RLSTD= float(S[1])
		if S[0] == "number_of_reads":
			NTR= float(S[1])
	FN  = MRL - RLSTD - H - T     
	if NTR >= minR and FN > L:
		DECISON = "accept"   
	return DECISON


def METAdataExtract (filepath):
	FileName, IDname, Header, dataInfo, n = [],[] , "", [], 0 
	f = open (filepath, "r" )
	extension = filepath.split(".")[-1]
	if  extension == "tsv":
		S = "\t"
	else:
		S = ","
	for line in f:
		if line[0] != "#":
			if n == 0:
				HeaderInfo = line.split(S)
				Header = HeaderInfo[0]
				for H in HeaderInfo[1:]:
					Header = Header + "," + H.split("\n")[0]
			if n > 0 :
				meta = line.split(S)
				row = meta[0] 
				for D in meta[1:]:
					row = row + "," + D.split("\n")[0]
				dataInfo.append(row)
				FileName.append(line.split(S)[1].split("\n")[0])
				IDname.append(line.split(S)[0].split("\n")[0]) 
			n = n + 1
	f.close()
	return [Header, IDname, FileName, dataInfo ]

def ID_files_renamming(path, name):
	files = os.listdir(path)
	for File in files:
		OldFilePath = path+"/"+ File
		NewFile = name+"."+File
		os.rename(OldFilePath, path+"/"+ NewFile)


def pipeline():
    start = time.time()
    print ("===============================================================================")
    print ("  AUTOMATED PIPELINE alpha for miniON NGS data processing  (alpha version)  ")
    print ("===============================================================================")
    if ARGS.PATH == "choose":
        Tk().withdraw()
        path = askdirectory(title = "open folder with  multiple sample reads files from MiniON" )
    else:
        path = ARGS.PATH

    if ARGS.REFGENOME == "choose":      
        Tk().withdraw()
        RefGenome_path = filedialog.askopenfilename( title = "open reference genome fasta file", filetypes=[("fasta","*.fasta")] )
    else:
        RefGenome_path = ARGS.REFGENOME 

    if ARGS.META == "choose":      
        Tk().withdraw()
        metapath = filedialog.askopenfilename( title = "open metadata file", filetypes=[("csv files","*.csv"), ("tsv files","*.tsv") ] )
        metadata = METAdataExtract(metapath)
    else:
        metadata = METAdataExtract(ARGS.META)
    FILES = os.listdir (path)
    RUNfolder = ARGS.RUN_NAME
    model = ARGS.MODEL            
    coverage_cutoff = ARGS.CUTOFF1       
    ideal_cutoff = ARGS.IDEAL_COVERAGE  
    minQReads  = ARGS.MINQREADS            
    headcrop = ARGS.HEADCROP                        
    tailcrop = ARGS.TAILCROP                   
    minLen = ARGS.MINRLENGHT                   
    minfreq = ARGS.MINFREQ                       
    maxINDELs = ARGS.MAXINDEL                    
    cutRegions = ARGS.IGNORE_REGIONS             
    minReads  = ARGS.MINREADSN                   
    minCOV2 = ARGS.MINSEQCOV                     
    if not os.path.exists(path + "/" + RUNfolder):
        os.mkdir(path + "/" + RUNfolder)
    else:
        CHOICE = input( "Analysis name already exists! Press y to continue (it carries on the remaining files to be processed) :\n")
        if CHOICE != "y":
            print("Please run again the tool and provide a new analysis name")
            exit(0)                         
    Headers = "NO"
    if not os.path.exists(path + "/" + RUNfolder + "/miniON_Data_ProcessingReport.csv"):
	    Headers = "YES"
    ReportFile = open(path + "/" + RUNfolder + "/miniON_Data_ProcessingReport.csv", "a")
    MutationsFile = open(path + "/" + RUNfolder + "/Detected_Mutations.csv", "a")
    if Headers == "YES":
	    ColumnsNames = metadata[0] + ",Mean Read Quality,Mean Reads Size,Total Number Reads,Total Number Bases,Average Coverage,Consensus sequence coverage,Number Masked Bases,Detected mutations,Number Insertions,Number Deletions,Sequence gaps, Mean Read Quality After Filter,Mean Reads Size After Filter,Number Reads After Filter,Number Bases After Filter,Sample Status\n"  
	    MutationsFile.write("Sample Number,Sample ID,Mutation,Type,Locus,Position,Frequency,Coverage\n") 
	    ReportFile.write(ColumnsNames) 
    Rejected_data = []
    DATE = datetime.datetime.now() 
    N, T = 0, 0 
    for FileName in FILES:
        fileType, RUNsample = "none", "Ignore"
        Fi = FileName.split(".")
        if len(FileName.split(".")) > 1 and len(FileName.split("_HQ") ) == 1:
            fileType = FileName.split(".")[1]
            if fileType == "fastq":
                T = T + 1
                sample_reads_path = path + "/" + FileName
                sampleIDname = Get_Sample_IDname(sample_reads_path)	
                if not os.path.exists(path + "/" + RUNfolder + "/" + sampleIDname ):
                    RUNsample = "YES"
        if fileType == "fastq" and RUNsample != "Ignore" and (FileName in metadata[2]):
            N = N +1
            print("\n\n\n ...processing sample ", T, "(",FileName.split(".")[0], ")"  )
            sample_reads_path = path + "/" + FileName		
            sampleIDname = Get_Sample_IDname(sample_reads_path)
            sampleInfo = ""
            for i, info in enumerate(metadata[2]):
                if info == FileName or metadata[1][i] == sampleIDname:
                    sampleInfo = metadata[3][i] 
            outputpath = path + "/" + RUNfolder + "/" + sampleIDname
            TemporarySTATS = path + "/" + RUNfolder + "/temporary.txt"
            QCcheck1 = BADsampleCheker( sample_reads_path , TemporarySTATS , headcrop , tailcrop, minLen, minReads )
            if minQReads == 0 and QCcheck1 != "reject":
                HQsample_reads_path = sample_reads_path
                QCcheck2 = QCcheck1 
            if minQReads != 0 and QCcheck1 != "reject":
                HQsample_reads_path = HQfilterReads( sample_reads_path, minQReads, headcrop, tailcrop, minLen  )
                QCcheck2 = BADsampleCheker( HQsample_reads_path , TemporarySTATS , headcrop , tailcrop, minLen, minReads )
            if QCcheck1 != "reject" and QCcheck2 != "reject":
                MedakaOutputs = Medaka_consensus_prediction (HQsample_reads_path , RefGenome_path , model, outputpath)
                Consensus = MedakaOutputs[2]   
                ProbFile = MedakaOutputs[1]    
                BAMfile = MedakaOutputs[0]  
                final_reads_stats = Reads_Stats(HQsample_reads_path, outputpath , "FilteredStatsReport") 
                sample_reads_stats = Reads_Stats(sample_reads_path, outputpath , "InitialStatsReport")
                SampleCoverageFile = CoverageExtraction(BAMfile)
                VCFfile = VariantCalling_Medaka(ProbFile, RefGenome_path, BAMfile)
                BadReg = Generate_Bad_regions_index (cutRegions)
                Refine_medaka_VCF_with_coverage_and_frequency (VCFfile,coverage_cutoff , BadReg, minfreq , maxINDELs)
                MutINFO = Get_Variant_INFO_fromVCF(VCFfile ) 
                VCF_TO_CONSENSUS_bcftools( VCFfile, Consensus, RefGenome_path, outputpath  )
                consensus_sequence_unmasked = import_seqs(Consensus)
                reference_sequence = import_seqs(RefGenome_path)
                Allign_seqs = []
                for seg in range(len(reference_sequence)): 
                    Allign_file = Run_Alingment_MAFFT ( reference_sequence[seg] , consensus_sequence_unmasked[seg] , outputpath ) 
                    Allign_seqs =  Allign_seqs + import_seqs(Allign_file)
                Mask =  LowCov_SeqMasker (Allign_seqs, SampleCoverageFile  , Consensus, coverage_cutoff, BadReg)
                DepthVALUES = CoverageQuality_Plot( coverage_cutoff , ideal_cutoff, SampleCoverageFile , MutINFO )
                mutation_count, tI, tD = 0, 0,0   
                for i, INFO in enumerate(MutINFO[0]):
                    Pi = int(float(INFO))
                    Muti = MutINFO[1][i]
                    FREQi = float(MutINFO[2][i])
                    Typi = MutINFO[3][i] 
                    Covi = int(float(MutINFO[5][i])) 
                    seqi = MutINFO[4][i]       
                    mutation_count = mutation_count + 1
                    MutationsFile.write(  str(N) + "," + sampleIDname + "," +   Muti   + "," +  Typi  + "," +  seqi   + "," + str(Pi) + "," +  str(FREQi)  + "," + str(Covi) + "\n"  )
                    if Typi =="Insertion":
                        tI += tI + 1
                    if Typi =="Deletion":
                        tD = tD + 1  
                ISD = final_reads_stats
                SSD = sample_reads_stats
                SampleSequenceCoverage = round( (Mask[1] - Mask[0])/ Mask[1] *100 , 1 )
                if SampleSequenceCoverage > minCOV2 :
                    Message = "Sample with good quality"
                else:
                    Message = "Warning: Not enough sequence coverage"
                C2, C3, C4, C5 = str(SSD[2]).split("\n")[0] , str(SSD[0]).split("\n")[0], str(SSD[3]).split("\n")[0], str(SSD[4]).split("\n")[0] 
                C6, C7, C8, C10, C11, C12 =str(int((sum(DepthVALUES)/len(DepthVALUES) ))),  str(SampleSequenceCoverage), str(Mask[0]),  str(tI) , str(tD)  , str(Mask[3])
                C13, C14, C15, C16 = str(ISD[2]).split("\n")[0], str(ISD[0]).split("\n")[0], str(ISD[3]).split("\n")[0], str(ISD[4]).split("\n")[0]  
                C9, C1  = str(mutation_count), Message
                ColumnValues = sampleInfo + "," + C2+ "," + C3+ "," + C4 + "," + C5 + "," + C6+ "," + C7+ "," + C8+ "," + C9+ "," + C10+ "," + C11+"," + C12 +"," +  C13+"," + C14+"," + C15+"," + C16+ "," + C1 +  "\n"
                ReportFile.write(ColumnValues)
                avTime = float(time.time() - start)/N
                WriteParametersReport ( path + "/" + RUNfolder + "/" , RefGenome_path, model,coverage_cutoff, minQReads, headcrop, tailcrop, cutRegions, RUNfolder, T, avTime, DATE ) 
                GunZip_Files( [ SampleCoverageFile ] )
                RefHeader = [ seqinfo[0] for seqinfo in reference_sequence ]
                Add_SampleIDinfo_fasta( Consensus , sampleIDname, RefHeader )     #  Manipulation of Consensus file header 
                UnecessaryFiles_remove(RefGenome_path, sample_reads_path, outputpath, TemporarySTATS, minQReads) 
                ID_files_renamming( outputpath,  sampleIDname )
            if QCcheck1 == "reject" or QCcheck2 == "reject":
                Rejected_data.append(sampleIDname)
                if QCcheck1 != "reject":
                    os.remove(HQsample_reads_path)
    pTime = time.time() - start
    print ("\n\nREPORT SUMMARY")
    print ("================================================================================================")
    print ("              Total number of samples analysed    = ", T )
    print ("              Total number of samples rejected    = ", len(Rejected_data) )
    print ("              Total number of samples acceptable  = ", T - len(Rejected_data)   )
    print ("              Total pipeline processing time      = ", round(pTime/60 , 1 ), " minutes ")
    print ("              Average processing time per sample  = ", round(pTime/N/60 , 1 ), " minutes ")
    print ("================================================================================================")
    print("\n\nRejected samples with not enough data quality for analysis:\n")
    RejS = ""
    for S in Rejected_data:
        RejS = RejS + "\t" + S 
    print (RejS)
    print ("\n**********************END**OF*PROCESS*****THANK*YOU*********************************************")
    print ("      alpha version tool developed by Ricardo Jorge Pais (last updated on April 2021)             ")
    print ("************************************************************************************************")
    ReportFile.close()
    MutationsFile.close()

if __name__ == "__main__":
    pipeline() 
