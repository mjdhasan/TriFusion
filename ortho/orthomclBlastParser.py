#!/usr/bin/python2

import os
import sqlite3 as lite

VAR_LENGTH = 0
VAR_TAXON = 1
cur = None

"""
Read all fasta files from a folder, placing the genes present on those fasta
into a single variable
"""


def get_genes(files_dir):

    genes = {}

    # Filter hidden files and not fasta files (from extension)
    files_list = [x for x in os.listdir(files_dir)
                  if not x.startswith(".") or
                  x.endswith(".fasta") or
                  x.endswith(".fas") or
                  x.endswith(".fa")]

    # for all fast files in fasta directory
    for fasta in files_list:

        # get taxon from file name
        splitted = fasta.split(".")
        taxon = splitted[0]

        # open file
        fasta_file = open(os.path.join(files_dir, fasta), "r")

        gene = ''
        length = 0
        for line in fasta_file:
            # clean '\n'
            line = line.strip()
            # ignore empty lines and stop codons
            if not line: # or line.endswith("*"):
                continue

            new_gene = True if line.startswith(">") else False

            if new_gene:
                # save previous gene info
                if gene:
                    genes[gene][VAR_LENGTH] = length

                # save new gene info
                gene = line[1:]
                genes[gene] = [None, taxon]

                # reset vars
                length = 0
            else:
                length += len(line)

        genes[gene][VAR_LENGTH] = length

        fasta_file.close()

    return genes


def get_taxon_and_length(subject, genes):

    subject["queryTaxon"] = genes[subject["queryId"]][VAR_TAXON]
    subject["subjectTaxon"] = genes[subject["subjectId"]][VAR_TAXON]
    subject["queryLength"] = genes[subject["queryId"]][VAR_LENGTH]
    subject["subjectLength"] = genes[subject["subjectId"]][VAR_LENGTH]

    try:
        subject["subjectTaxon"]
    except KeyError:
        print ("couldn't find taxon for gene " + subject["subjectId"])
    try:
        subject["queryTaxon"]
    except KeyError:
        print ("couldn't find taxon for gene " + subject["queryId"])

    return int(subject["queryLength"]) < int(subject["subjectLength"])


def print_previous_subject(subject, db):

    non_overlap = non_overlapping_match(subject)

    percent_ident = '{0:.3g}'.format(
        (float(subject["totalIdentities"]) /
         float(subject["totalLength"]) * 10 + .5) / 10)
    
    shorter_length = subject["queryLength"] if subject["queryShorter"] \
        else subject["subjectLength"]

    percent_match = '{0:.3g}'.format((float(non_overlap) /
                                      float(shorter_length) * 1000 + .5) / 10)

    db.execute("INSERT INTO SimilarSequences VALUES(?, ?, ?, ?, ?, ? ,?, ?)",
                [subject["queryId"],
                 subject["subjectId"],
                 subject["queryTaxon"],
                 subject["subjectTaxon"],
                 float(subject["evalueMant"]),
                 int(subject["evalueExp"]),
                 float(percent_ident),
                 float(percent_match)])


# this (corrected) version of formatEvalue provided by Robson de Souza
def format_evalue(evalue):
    if evalue == '0':
        return 0, 0
    if evalue.startswith('e'):
        evalue = '1' + evalue

    return [round(float(x), 2) for x in evalue.split("e")]


def non_overlapping_match(subject):

    # flatten lists
    hsps = subject["hspspans"]
    hsps.sort(key=lambda x: x[0])
    original = hsps.pop(0)

    original = (int(original[0]), int(original[1]))

    start = 0
    end = 1
    
    if not original:
        return 0

    original = get_start_end(original)
    length = 0

    for h in hsps:
        h = get_start_end(h)
        # does not extend
        if h[end] < original[end]:
            continue
        # overlaps
        if h[start] <= original[end]:
            # extend end ... already dealt with if new end is less
            original = (original[start], h[end])
        # there is a gap in between
        else:
            length = original[end] - original[start] + 1
            original = (h[start], h[end])

    length += original[end] - original[start] + 1 # deal with the last one 
    return length


# flip orientation if nec.
def get_start_end(h):
    start = h[0]
    end = h[1]
    if start > end:
        end = h[0]
        start = h[1]
 
    return int(start), int(end)


def orthomcl_blast_parser(blast_file, fasta_dir, db_dir):

    # create connection to DB
    con = lite.connect(os.path.join(db_dir, "orthoDB.db"))
    with con:
        #global cur
        cur = con.cursor()

        # parse fasta files
        genes = get_genes(fasta_dir)
        blast_fh = open(blast_file, "r")

        prev_subjectid = ''
        prev_queryid = ''
        # hash to hold subject info
        subject = {}

        for line in blast_fh:
            splitted = line.split()

            query_id = splitted[0]
            subject_id = splitted[1]
            percent_identity = splitted[2]
            length = int(splitted[3])
            query_start = splitted[6]
            query_end = splitted[7]
            subject_start = splitted[8]
            subject_end = splitted[9]
            evalue = splitted[10]

            if query_id != prev_queryid or subject_id != prev_subjectid:

                # print previous subject
                if subject:
                    print_previous_subject(subject, cur)

                # initialize new one from first HSP
                prev_subjectid = subject_id
                prev_queryid = query_id

                # from first hsp
                tup = format_evalue(evalue)

                subject = {"queryId": query_id}
                subject["subjectId"] = subject_id
                subject["queryShorter"] = get_taxon_and_length(subject, genes)

                subject["evalueMant"] = tup[0]
                subject["evalueExp"] = tup[1]
                subject["totalIdentities"] = 0
                subject["totalLength"] = 0
                subject["hspspans"] = []

            # get additional info from subsequent HSPs
            hspspan = (subject_start, subject_end)
            if subject and subject["queryShorter"]:
                hspspan = (query_start, query_end)
            subject["hspspans"].append(hspspan)
            subject["totalIdentities"] += float(percent_identity) * length
            subject["totalLength"] += length

    #print_previous_subject(subject, cur)

    #con.close()
