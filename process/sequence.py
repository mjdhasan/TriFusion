#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  
#  Copyright 2012 Unknown <diogo@arch>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  Author: Diogo N. Silva
#  Version: 0.1.1
#  Last update: 11/02/14

from process.base import *
from process.missing_filter import MissingFilter
#from process.error_handling import *

from collections import OrderedDict
import re

## TODO: Create a SequenceSet class for sets of sequences that do not conform
# to an alignment, i.e. unequal length.This would eliminate the problems of
# applying methods designed for alignments to sets of sequences with unequal
# length would allows these sets of sequences to have methods of their own.
# However, the __init__ of the current Alignment object should apply to both
# SequenceSet and Alignment classes. So, I'll have to re-structure the code
# somehow.
## TODO After creating the SequenceSet class, an additional class should be
# used to make the triage of files to either the Alignment or SequenceSet
# classes


class Alignment (Base, MissingFilter):

    def __init__(self, input_alignment, input_format=None, model_list=None,
                 alignment_name=None, loci_ranges=None):
        """ The basic Alignment class requires only an alignment file and
         returns an Alignment object. In case the class is initialized with
         a dictionary object, the input_format, model_list, alignment_name
         and loci_ranges arguments can be used to provide complementary
         information for the class. However, if the class is not initialized
         with specific values for these arguments, they can be latter set
         using the _set_format and _set_model functions

        The loci_ranges argument is only relevant when an Alignment object
        is initialized from a concatenated data set in which case it is
        relevant to incorporate this information in the object"""

        self.log_progression = Progression()
        # The locus_length and restriction_range variables are only properly
        # defined elsewhere, but to avoid NoneType
        # errors, it is defined here
        self.locus_length = 0
        self.restriction_range = None

        # Boolean attribute to know if Alignment object is truly an alignment
        #  or a sequence set
        self.is_alignment = None

        # Initialize loci_ranges attribute, which will inform if input
        # alignment is a concatenation or not
        self.loci_ranges = None

        # In case the class is initialized with an input file name
        if type(input_alignment) is str:

            self.name = input_alignment
            # Get alignment format and code. Sequence code is a tuple of
            # (DNA, N) or (Protein, X)
            finder_content = self.autofinder(input_alignment)
            # Handles the case where the input format is invalid and
            # finder_content is an Exception
            if isinstance(finder_content, Exception) is False:
                self.input_format, self.sequence_code = self.autofinder(
                    input_alignment)

                # In case the input format is specified, overwrite the attribute
                if input_format is not None:
                    self.input_format = input_format

                # parsing the alignment and getting the basic class attributes
                # Three attributes will be assigned: alignment, model and locus_
                # length
                self.read_alignment(input_alignment, self.input_format)
            else:
                self.alignment = finder_content

        # In case the class is initialized with a dictionary object
        elif type(input_alignment) is OrderedDict:

            # The name of the alignment (str)
            self.name = alignment_name
            # Gets several attributes from the dictionary alignment
            self.init_dicobj(input_alignment)
            #The input format of the alignment (str)
            self.input_format = input_format
            # A list containing the alignment model(s) (list)
            self.model = model_list
            if loci_ranges is not None:
                # A list containing the ranges of the alignment, in case it's a
                # concatenation
                self.loci_ranges = loci_ranges

    def _set_loci_ranges(self, loci_list):
        """ Use this function to manually set the list with the loci ranges """

        self.loci_ranges = loci_list

    def _set_format(self, input_format):
        """ Use this function to manually set the input format associated
        with the Alignment object """

        self.input_format = input_format

    def _set_model(self, model_list):
        """ Use this function to manually set the model associated with the
        Alignment object. Since this object supports concatenated alignments,
         the model specification must be in list format and the list size
         must be of the same size of the alignment partitions """

        self.model = model_list

    def _set_alignment(self, alignment_dict):
        """ This function can be used to set a new alignment dictionary to
        the Alignment object. This may be usefull when only the alignment
        dict of the object has to be modified through other
        objects/functions """

        self.alignment = alignment_dict

    # def _set_locus_length(self, locus_length):
    # 	""" Manually sets the length of the locus in the Alignment locus """

    def init_dicobj(self, dictionary_obj):
        """ In case the class is initialized with a dictionary as input, this
         function will retrieve the same information as the read_alignment
         function would do  """

        self.sequence_code = self.guess_code(list(dictionary_obj.values())[0])
        self.alignment = dictionary_obj
        self.locus_length = len(list(dictionary_obj.values())[0])

    def read_alignment(self, input_alignment, alignment_format,
                       size_check=True):
        """ The read_alignment method is run when the class is initialized to
        parse an alignment an set all the basic attributes of the class.

        The 'alignment' variable contains an ordered dictionary with the taxa
        names as keys and sequences as values. The 'model' is an non
        essential variable that contains a string with a substitution model
        of the alignment. This only applies to Nexus input formats, as it is
        the only supported format that contains such information The
        'locus_length' variable contains a int value with the length of the
        current alignment """

        # Storage taxa names and corresponding sequences in an ordered
        # Dictionary
        self.alignment = OrderedDict()

        # Only applies for nexus format. It stores any potential substitution
        #  model at the end of the file
        self.model = []

        file_handle = open(input_alignment)

        # PARSING PHYLIP FORMAT
        if alignment_format == "phylip":
            # Get the number of taxa and sequence length from the file header
            header = file_handle.readline().split()
            self.locus_length = int(header[1])
            for line in file_handle:
                try:
                    taxa = line.split()[0].replace(" ", "")
                    taxa = self.rm_illegal(taxa)
                    try:
                        sequence = line.split()[1].strip().lower()
                    except IndexError:
                        sequence = ""

                    self.alignment[taxa] = sequence
                except IndexError:
                    pass

                    ## TO DO: Read phylip interleave

        # PARSING FASTA FORMAT
        elif alignment_format == "fasta":
            for line in file_handle:
                if line.strip().startswith(">"):
                    taxa = line[1:].strip().replace(" ", "_")
                    taxa = self.rm_illegal(taxa)
                    self.alignment[taxa] = ""
                elif line.strip() != "" and taxa is not None:
                    self.alignment[taxa] += line.strip().lower().\
                        replace(" ", "")
            self.locus_length = len(list(self.alignment.values())[0])

        # PARSING NEXUS FORMAT
        elif alignment_format == "nexus":
            counter = 0
            for line in file_handle:
                # Skips the nexus header
                if line.strip().lower() == "matrix" and counter == 0:
                    counter = 1
                # Stop parser here
                elif line.strip() == ";" and counter == 1:
                    counter = 2
                # Start parsing here
                elif line.strip() != "" and counter == 1:
                    taxa = line.strip().split()[0].replace(" ", "")
                    taxa = self.rm_illegal(taxa)
                    # This accommodates for the interleave format
                    if taxa in self.alignment:
                        self.alignment[taxa] += "".join(
                            line.strip().split()[1:]).lower()
                    else:
                        self.alignment[taxa] = "".join(
                            line.strip().split()[1:]).lower()

                # This bit of code will extract a potential substitution model
                #  from the file
                elif counter == 2 and line.lower().strip().startswith("lset"):
                    self.model.append(line.strip())
                elif counter == 2 and line.lower().strip().startswith("prset"):
                    self.model.append(line.strip())

            self.locus_length = len(list(self.alignment.values())[0])

        # Checks the size consistency of the alignment
        if size_check is True:
            self.is_alignment = self.check_sizes(self.alignment,
                                                 input_alignment)

        # Checks for duplicate taxa
        if len(list(self.alignment)) != len(set(list(self.alignment))):
            taxa = self.duplicate_taxa(self.alignment.keys())
            self.log_progression.write("WARNING: Duplicated taxa have been "
                                       "found in file %s (%s). Please correct "
                                       "this problem and re-run the program\n"
                                       % (input_alignment, ", ".join(taxa)))
            raise SystemExit

    def iter_taxa(self):
        """ Returns a list with the taxa contained in the alignment """

        taxa = [sp for sp in self.alignment]

        return taxa

    def iter_sequences(self):
        """ Returns a list with the sequences contained in the alignment """

        sequences = [seq for seq in self.alignment]

        return sequences

    def remove_taxa(self, taxa_list_file, mode="remove"):
        """ Removes specified taxa from the alignment. As taxa_list, this
        method supports a python list or an input csv file with a single
        column containing the unwanted species in separate lines. It
        currently supports two modes:
            remove: removes the specified taxa
            inverse: removes all but the specified taxa """

        new_alignment = OrderedDict()

        def remove(list_taxa):

            for taxa, seq in self.alignment.items():
                if taxa not in list_taxa:
                    new_alignment[taxa] = seq

            self.alignment = new_alignment

        def inverse(list_taxa):

            for taxa, seq in self.alignment.items():
                if taxa in list_taxa:
                    new_alignment[taxa] = seq

            self.alignment = new_alignment

        # Checking if taxa_list is an input csv file:
        try:
            file_handle = open(taxa_list_file[0])

            taxa_list = self.read_basic_csv(file_handle)

        # If not, then the method's argument is already the final list
        except (FileNotFoundError, IndexError):
            taxa_list = taxa_list_file

        if mode == "remove":
            remove(taxa_list)
        if mode == "inverse":
            inverse(taxa_list)

    def collapse(self, write_haplotypes=True, haplotypes_file=None,
                 haplotype_name="Hap"):
        """
        Collapses equal sequences into haplotypes. This method changes
        the alignment variable and only returns a dictionary with the
        correspondence between the haplotypes and the original taxa names
        :param write_haplotypes: Boolean, If true, a haplotype list
        mapping the haplotype names file will be created for each individual
        input alignment.
        :param haplotypes_file: String, Name of the haplotype list mapping file
        referenced in write_haplotypes
        :param haplotype_name: String, Custom name of the haplotypes
        """

        collapsed_dic, correspondence_dic = OrderedDict(), OrderedDict()
        counter = 1

        for taxa, seq in self.alignment.items():
            if seq in collapsed_dic:
                collapsed_dic[seq].append(taxa)
            else:
                collapsed_dic[seq] = [taxa]

        self.alignment = OrderedDict()
        for seq, taxa_list in collapsed_dic.items():
            haplotype = "%s_%s" % (haplotype_name, counter)
            self.alignment[haplotype] = seq
            correspondence_dic[haplotype] = taxa_list
            counter += 1

        if write_haplotypes is True:
            # If no output file for the haplotype correspondence is provided,
            #  use the input alignment name as reference
            if haplotypes_file is None:
                haplotypes_file = self.name.split(".")[0]
            self.write_loci_correspondence(correspondence_dic, haplotypes_file)

    @staticmethod
    def write_loci_correspondence(dic_obj, output_file):
        """ This function supports the collapse method by writing the
        correspondence between the unique haplotypes and the loci into a
        new file """

        output_handle = open(output_file + ".haplotypes", "w")

        for haplotype, taxa_list in dic_obj.items():
            output_handle.write("%s: %s\n" % (haplotype, "; ".join(taxa_list)))

        output_handle.close()

    def reverse_concatenate(self, partition_obj):
        """ This function divides a concatenated file according previously
        defined partitions and returns an AlignmentList object """

        alignment_list, models, names = [], [], []

        for model, name, part_range in partition_obj.partitions:
            partition_dic = OrderedDict()
            for taxon, seq in self.alignment.items():
                sub_seq = seq[int(part_range[0]) - 1:int(part_range[1]) - 1]
                if sub_seq.replace(self.sequence_code[1], "") != "":
                    partition_dic[taxon] = sub_seq
            alignment_list.append(partition_dic)
            models.append(model)
            names.append(name)

        alignmentlist_obj = AlignmentList(alignment_list, model_list=models,
                                          name_list=names,
                                          input_format=self.input_format)

        return alignmentlist_obj

    def code_gaps(self):
        """ This method codes gaps present in the alignment in binary format,
         according to the method of Simmons and Ochoterena (2000), to be read
         by phylogenetic programs such as MrBayes. The resultant alignment,
          however, can only be output in the Nexus format """

        def gap_listing(sequence, gap_symbol="-"):
            """ Function that parses a sequence string and returns the
            position of indel events. The returned list is composed of
            tuples with the span of each indel """
            gap = "%s+" % gap_symbol
            span_regex = ""
            gap_list, seq_start = [], 0
            while span_regex is not None:
                span_regex = re.search(gap, sequence)
                if span_regex is not None and seq_start == 0:
                    gap_list.append(span_regex.span())
                    sequence = sequence[span_regex.span()[1] + 1:]
                    seq_start = span_regex.span()[1] + 1
                elif span_regex is not None and seq_start != 0:
                    gap_list.append((span_regex.span()[0] + seq_start,
                                     span_regex.span()[1] + seq_start))
                    sequence = sequence[span_regex.span()[1] + 1:]
                    seq_start += span_regex.span()[1] + 1
            return gap_list

        def gap_binary_generator(sequence, gap_list):
            """ This function contains the algorithm to construct the binary
             state block for the indel events """
            for cur_gap in gap_list:
                cur_gap_start, cur_gap_end = cur_gap
                if sequence[cur_gap_start:cur_gap_end] == "-" * \
                        (cur_gap_end - cur_gap_start) and \
                        sequence[cur_gap_start - 1] != "-" and \
                        sequence[cur_gap_end] != "-":
                    sequence += "1"

                elif sequence[cur_gap_start:cur_gap_end] == "-" * \
                     (cur_gap_end - cur_gap_start):

                    if sequence[cur_gap_start - 1] == "-" or \
                    sequence[cur_gap_end] == "-":
                        sequence += "-"

                elif sequence[cur_gap_start:cur_gap_end] != "-" * \
                        (cur_gap_end - cur_gap_start):
                    sequence += "0"
            return sequence

        complete_gap_list = []

        # Get the complete list of unique gap positions in the alignment
        for taxa, seq in self.alignment.items():

            current_list = gap_listing(seq)
            complete_gap_list += [gap for gap in current_list if gap not in
                                  complete_gap_list]

        # This will add the binary matrix of the unique gaps listed at the
        # end of each alignment sequence
        for taxa, seq in self.alignment.items():
            self.alignment[taxa] = gap_binary_generator(seq, complete_gap_list)

        self.restriction_range = "%s-%s" % (int(self.locus_length),
                                            len(complete_gap_list) +
                                            int(self.locus_length) - 1)

    def filter_missing_data(self, gap_threshold, missing_threshold):
        """ Wraps the MissingFilter class """

        # When the class is initialized, it performs the basic filtering
        # operations based on the provided thresholds
        alignment_filter = MissingFilter(self.alignment,
                                         gap_threshold=gap_threshold,
                                        missing_threshold=missing_threshold,
                                        gap_symbol="-",
                                        missing_symbol=self.sequence_code[1])

        # Replace the old alignment by the filtered one
        self.alignment = alignment_filter.alignment
        self.locus_length = alignment_filter.locus_length

    def write_to_file(self, output_format, output_file, new_alignment=None,
                      seq_space_nex=40, seq_space_phy=30, seq_space_ima2=10,
                      cut_space_nex=50, cut_space_phy=50, cut_space_ima2=8,
                      interleave=False, gap="-", model_phylip="LG",
                      outgroup_list=None, ima2_params=None,
                      partition_file=True):
        """ Writes the alignment object into a specified output file,
        automatically adding the extension, according to the output format
        This function supports the writing of both converted (no partitions)
        and concatenated (partitioned files). The choice of this modes is
        determined by the presence or absence of the loci_range attribute of
        the object. If its None, there are no partitions and no partitions
        files will be created. If there are partitions, then the appropriate
        partitions will be written. The outgroup_list argument is used only
        for Nexus output format and consists in writing a line defining the
        outgroup. This may be useful for analyses with MrBayes or other
        software that may require outgroups

        The ima2_params argument is used to provide information for the
        ima2 output format. If the argument is used,
        it should be in a list format and contain the following information:
          [[str, file_name containing the species and populations],
          [str, the population tree in newick format, e.g. (0,1):2],
          [mut_model:[str, mutational model for all alignments],
          [str, inheritance scalar]]
        """

        # If this function is called in the AlignmentList class, there may
        # be a need to specify a new alignment dictionary, such as a
        # concatenated one
        if new_alignment is not None:
            alignment = new_alignment
        else:
            alignment = self.alignment

        # Checks if there is any other format besides Nexus if the
        # alignment's gap have been coded
        if self.restriction_range is not None:
            if output_format != ["nexus"]:
                self.log_progression.write("OutputFormatError: Alignments "
                                           "with gaps coded can only be written"
                                           " in Nexus format")
                return 0
        else:
            pass

        # Writes file in IMa2 format
        if "ima2" in output_format:

            population_file = ima2_params[0]
            population_tree = ima2_params[1]
            mutational_model = ima2_params[2]
            inheritance_scalar = ima2_params[3]

            # Get information on which species belong to each population from
            #  the populations file
            population_handle = open(population_file)
            population_storage = OrderedDict()
            for line in population_handle:
                taxon, population = re.split(r'[\t;,]', line)
                try:
                    population_storage[population.strip()].append(taxon)
                except KeyError:
                    population_storage[population.strip()] = [taxon]

            # Write the general header of the IMa2 input file
            out_file = open(output_file + ".txt", "w")
             # First line with general description
            out_file.write("Input file for IMa2 using %s alignments\n"
                        "%s\n"  # Line with number of loci
                        "%s\n"  # Line with name of populations
                        "%s\n"  # Line with population string
                        % (len(self.loci_ranges), len(population_storage),
                           " ".join(population_storage.keys()),
                           population_tree))

            if self.loci_ranges is not None:
                # Write each locus
                for partition, lrange in self.loci_ranges:

                    # Defining a list variable with the range of the current
                    #  loci
                    partition_range = lrange.split("-")

                    # Retrieving taxon names and sequence data. This step is
                    # the first because it will enable the removal of species
                    #  containing only missing data.
                    new_alignment = []

                    # This temporary ordered dictionary is created so that
                    #  the number of taxa per populations is corrected in
                    # each locus
                    current_locus_populations = OrderedDict(
                        (x, []) for x in population_storage)

                    for population, taxa_list in population_storage.items():
                        for taxon in taxa_list:
                            # This try statement catches common errors, such as
                            #  providing a species in the mapping file that
                            # does not exist in the alignment
                            try:
                                seq = self.alignment[taxon][
                                      (int(partition_range[0]) - 1):
                                      (int(partition_range[1]) - 1)].upper()
                            except KeyError:
                                print("Taxon %s provided in auxiliary "
                                      "population mapping file is not found "
                                      "in the alignment")
                                raise SystemExit

                            if seq.replace("N", "") != "":
                                new_alignment.append((taxon[:cut_space_ima2]
                                                      .ljust(seq_space_ima2),
                                                      seq))

                                current_locus_populations[population]\
                                    .append(taxon)

                    # Write the header of each partition
                    out_file.write("%s %s %s %s %s\n" % (
                        partition,
                        " ".join([str(len(x)) for x in
                                  list(current_locus_populations.values())]),
                        (int(partition_range[1]) - int(partition_range[0])),
                        mutational_model,
                        inheritance_scalar))

                    # Write sequence data according to the order of the
                    # population mapping file
                    for taxon, seq in new_alignment:
                        out_file.write("%s%s\n" % (taxon, seq))

            if self.loci_ranges is None:
                #Write the header for the single
                out_file.write("%s %s %s %s %s\n" % (
                               partition,
                               " ".join(population_storage.values()),
                               self.locus_length,
                               mutational_model,
                               inheritance_scalar))

                #Write sequence data
                for population, taxa_list in population_storage.items():
                    for taxon in taxa_list:
                        seq = self.alignment[taxon].upper()
                        out_file.write("%s%s\n" %
                                      (taxon[:cut_space_ima2].ljust(
                                         seq_space_ima2),
                                       seq))

        # Writes file in phylip format
        if "phylip" in output_format:

            out_file = open(output_file + ".phy", "w")
            out_file.write("%s %s\n" % (len(alignment), self.locus_length))
            for key, seq in alignment.items():
                    out_file.write("%s %s\n" % (
                                   key[:cut_space_phy].ljust(seq_space_phy),
                                   seq.upper()))

            # In case there is a concatenated alignment being written
            if self.loci_ranges is not None and partition_file:
                partition_file = open(output_file + "_part.File", "a")
                for partition, lrange in self.loci_ranges:
                    partition_file.write("%s, %s = %s\n" % (
                                         model_phylip,
                                         partition,
                                         lrange))
            else:
                pass

            out_file.close()

        if "mcmctree" in output_format:

            out_file = open(output_file + ".phy", "w")
            taxa_number = len(self.alignment)

            if self.loci_ranges is not None:
                for element in self.loci_ranges:
                    partition_range = [int(x) for x in element[1].split("-")]
                    out_file.write("%s %s\n" % (
                                   taxa_number,
                                   (int(partition_range[1]) -
                                    int(partition_range[0]))))

                    for taxon, seq in self.alignment.items():
                        out_file.write("%s  %s\n" % (
                                       taxon[:cut_space_phy].ljust(
                                         seq_space_phy),
                                       seq[(int(partition_range[0]) - 1):
                                           (int(partition_range[1]) -
                                            1)].upper()))
            else:
                out_file.write("%s %s\n" % (taxa_number, self.locus_length))
                for taxon, seq in self.alignment.items():
                    out_file.write("%s  %s\n" % (
                                   taxon[:cut_space_phy].ljust(seq_space_phy),
                                   seq.upper()))

            out_file.close()

        # Writes file in nexus format
        if "nexus" in output_format:

            out_file = open(output_file + ".nex", "w")

            # This writes the output in interleave format
            if interleave:
                if self.restriction_range is not None:
                    out_file.write("#NEXUS\n\nBegin data;\n\tdimensions "
                                   "ntax=%s nchar=%s ;\n\tformat datatype="
                                   "mixed(%s:1-%s, restriction:%s) interleave="
                                   "yes gap=%s missing=%s ;\n\tmatrix\n" %
                                   (len(alignment),
                                    self.locus_length,
                                    self.sequence_code[0],
                                    self.locus_length - 1,
                                    self.restriction_range,
                                    gap,
                                    self.sequence_code[1]))
                else:
                    out_file.write("#NEXUS\n\nBegin data;\n\tdimensions "
                                   "ntax=%s nchar=%s ;\n\tformat datatype=%s "
                                   "interleave=yes gap=%s missing=%s ;\n\t"
                                   "matrix\n" % (
                                   len(alignment),
                                   self.locus_length,
                                   self.sequence_code[0], gap,
                                   self.sequence_code[1]))
                counter = 0
                for i in range(90, self.locus_length, 90):
                    for key, seq in alignment.items():
                        out_file.write("%s %s\n" % (
                                       key[:cut_space_nex].ljust(
                                         seq_space_nex),
                                       seq[counter:i].upper()))
                    else:
                        out_file.write("\n")
                        counter = i
                else:
                    for key, seq in alignment.items():
                        out_file.write("%s %s\n" % (
                                       key[:cut_space_nex].ljust(
                                         seq_space_nex),
                                       seq[i:self.locus_length].upper()))
                    else:
                        out_file.write("\n")
                out_file.write(";\n\tend;")

            # This writes the output in leave format (default)
            else:
                if self.restriction_range is not None:
                    out_file.write("#NEXUS\n\nBegin data;\n\tdimensions "
                                   "ntax=%s nchar=%s ;\n\tformat datatype=mixed"
                                   "(%s:1-%s, restriction:%s) interleave=yes "
                                   "gap=%s missing=%s ;\n\tmatrix\n" %
                                   (len(alignment),
                                    self.locus_length,
                                    self.sequence_code[0],
                                    self.locus_length - 1,
                                    self.restriction_range,
                                    gap,
                                    self.sequence_code[1]))
                else:
                    out_file.write("#NEXUS\n\nBegin data;\n\tdimensions ntax=%s"
                                   " nchar=%s ;\n\tformat datatype=%s "
                                   "interleave=no gap=%s missing=%s ;\n\t"
                                   "matrix\n" % (
                                    len(alignment),
                                    self.locus_length,
                                    self.sequence_code[0],
                                    gap, self.sequence_code[1]))

                for key, seq in alignment.items():
                    out_file.write("%s %s\n" % (key[:cut_space_nex].ljust(seq_space_nex), seq))
                out_file.write(";\n\tend;")

            try:
                self.loci_ranges
                out_file.write("\nbegin mrbayes;\n")
                for partition, lrange in self.loci_ranges:
                    out_file.write("\tcharset %s = %s;\n" % (partition, lrange))

                out_file.write("\tpartition part = %s: %s;\n\tset partition="
                               "part;\nend;\n" % (
                               len(self.loci_ranges),
                               ", ".join([part[0] for part in
                                          self.loci_ranges])))
            except:
                pass

            # In case outgroup taxa are specified
            if outgroup_list is not None:

                # This assures that only the outgroups present in the current
                #  file are written
                compliant_outgroups = [taxon for taxon in outgroup_list
                                       if taxon in self.iter_sequences()]
                if compliant_outgroups is not []:
                    out_file.write("\nbegin mrbayes;\n\toutgroup %s\nend;\n" %
                                   (" ".join(compliant_outgroups)))

            # Concatenates the substitution models of the individual partitions
            if self.model:
                loci_number = 1
                out_file.write("begin mrbayes;\n")
                for model in self.model:
                    m1 = model[0].split()
                    m2 = model[1].split()
                    m1_final = m1[0] + " applyto=(" + str(loci_number) + \
                               ") " + " ".join(m1[1:])
                    m2_final = m2[0] + " applyto=(" + str(loci_number) + \
                               ") " + " ".join(m2[1:])
                    out_file.write("\t%s\n\t%s\n" % (m1_final, m2_final))
                    loci_number += 1
                out_file.write("end;\n")

            out_file.close()

        # Writes file in fasta format
        if "fasta" in output_format:
            out_file = open(output_file + ".fas", "w")
            for key, seq in self.alignment.items():
                out_file.write(">%s\n%s\n" % (key, seq.upper()))

            out_file.close()


class AlignmentList (Alignment, Base, MissingFilter):
    """ At the most basic instance, this class contains a list of Alignment
    objects upon which several methods can be applied. It only requires either
     a list of alignment files or. It inherits methods from Base and
     Alignment classes for the write_to_file methods """

    def __init__(self, alignment_list, model_list=None, name_list=None,
                 verbose=True, input_format=None):

        self.log_progression = Progression()

        self.alignment_object_list = []
        # Stores badly formatted/invalid input alignments
        self.bad_alignments =[]

        if type(alignment_list[0]) is str:

            self.log_progression.record("Parsing file", len(alignment_list))
            for alignment in alignment_list:

                if verbose is True:
                    self.log_progression.progress_bar(
                        alignment_list.index(alignment) + 1)

                alignment_object = Alignment(alignment)
                if isinstance(alignment_object.alignment, Exception):
                    self.bad_alignments.append(alignment_object)
                else:
                    self.alignment_object_list.append(alignment_object)

        elif type(alignment_list[0]) is OrderedDict:

            # Setting class flag so that the object is aware that is a result
            #  of reverse concatenation and not an actual list of alignments
            self.reverse_concatenation = True

            for alignment, model, name in zip(alignment_list, model_list,
                                              name_list):

                alignment_object = Alignment(alignment, model_list=[model],
                                             alignment_name=name)
                # In some cases, like reverse concatenating, the input format
                #  must be manually set
                if input_format is not None:
                    alignment_object._set_format(input_format)
                self.alignment_object_list.append(alignment_object)

        #### SETTING GENERAL ATTRIBUTES

        # list of file names, complete with path
        self.filename_list = self._get_filename_list()

        # list of taxon names
        self.taxa_names = self._get_taxa_list()

    def __iter__(self):
        """
        Iterate over Alignment objects
        """
        return iter(self.alignment_object_list)

    def _get_format(self):
        """ Gets the input format of the first alignment in the list """

        return self.alignment_object_list[0].input_format

    def _get_taxa_list(self):
        """ Gets the full taxa list of all alignment objects """

        full_taxa = []

        for alignment in self.alignment_object_list:

            diff = set(alignment.iter_taxa()) - set(full_taxa)

            if diff != set():

                full_taxa.extend(diff)

        return full_taxa

    def _get_filename_list(self):
        """
        Returns a list with the input file names
        """
        return [alignment.name for alignment in self.alignment_object_list]

    def add_alignment(self, alignment_obj):
        """
        Adds a new Alignment object
        """

        self.alignment_object_list.append(alignment_obj)

        # Update taxa names with the new alignment
        self.taxa_names = self._get_taxa_list()

    def retrieve_alignment(self, name):
        """
        :param name: string. Name of the input alignment
        :return: Returns an Alignment object with a given name attribute
        """

        alignment_obj = [x for x in self.alignment_object_list if x.name ==
                         name][0]

        if alignment_obj:
            return alignment_obj
        else:
            return None

    def iter_alignment_dic(self):
        """ Returns a list of the dictionary alignments """

        return [alignment.alignment for alignment in self.alignment_object_list]

    def iter_alignment_obj(self):
        """ Returns a list of the alignments objects """

        return [alignment for alignment in self.alignment_object_list]

    def write_taxa_to_file(self):
        """
        Compiles the taxa names of all alignments and writes them in a single
         column .csv file
        """

        output_handle = open("Taxa_list.csv", "w")

        for taxon in self._get_taxa_list():
            output_handle.write(taxon + "\n")

        output_handle.close()

    def concatenate(self, progress_stat=True):
        """ The concatenate method will concatenate the multiple sequence
        alignments and create several attributes This method sets the first
        three variables below and the concatenation variable containing the
         dict object"""

        self.log_progression.record("Concatenating file", len(
                                    self.alignment_object_list))

        taxa_list = self._get_taxa_list()

        # Initializing alignment dict and other variables
        self.concatenation = OrderedDict([(key, []) for key in taxa_list])
        # Saves the sequence lengths of the
        self.loci_lengths = []
        # Saves the loci names as keys and their range as values
        self.loci_range = []
        # Saves the substitution models for each one
        self.models = []

        for alignment_object in self.alignment_object_list:

            # When set to True, this statement produces a progress status on
            # the terminal
            if progress_stat is True:
                self.log_progression.progress_bar(self.alignment_object_list.
                                                  index(alignment_object) + 1)

            # Setting the missing data symbol
            missing = alignment_object.sequence_code[1]

            # If input format is nexus, save the substitution model, if any
            if alignment_object.input_format == "nexus" and \
                            alignment_object.model != []:
                self.models.append(alignment_object.model)

            for taxa in taxa_list:
                try:
                    sequence = alignment_object.alignment[taxa]
                    self.concatenation[taxa].append(sequence)
                except:
                    self.concatenation[taxa].append(missing
                                             * alignment_object.locus_length)

            # Saving the range for the subsequent loci
            self.loci_range.append((alignment_object.name.split(".")
                                    [0], "%s-%s" % (sum(self.loci_lengths)
                                    + 1, sum(self.loci_lengths)
                                    + alignment_object.locus_length)))

            self.loci_lengths.append(alignment_object.locus_length)

        for taxa, seq in self.concatenation.items():
            self.concatenation[taxa] = "".join(seq)

        concatenated_alignment = Alignment(self.concatenation,
                                           input_format=self._get_format(),
                                           model_list=self.models,
                                           loci_ranges=self.loci_range)

        return concatenated_alignment

    def filter_missing_data(self, gap_threshold, missing_threshold,
                            verbose=True):
        """ Wrapper of the MissingFilter class that iterates over multiple
        Alignment objects """

        self.log_progression.record("Filtering file",
                                    len(self.alignment_object_list))
        for alignment_obj in self.alignment_object_list:

            if verbose is True:
                self.log_progression.progress_bar(
                    self.alignment_object_list.index(alignment_obj))

            alignment_obj.filter_missing_data(gap_threshold=gap_threshold,
                          missing_threshold=missing_threshold)

    def remove_taxa(self, taxa_list, verbose=False, mode="remove"):
        """ Wrapper of the remove_taxa method of the Alignment object for
         multiple alignments. It current supports two modes:
            remove: removes specified taxa
            inverse: removes all but the specified taxa """

        if verbose is True:
            self.log_progression.write("Removing taxa")

        for alignment_obj in self.alignment_object_list:

            alignment_obj.remove_taxa(taxa_list, mode=mode)

        # Updates taxa names
        self.taxa_names = self._get_taxa_list()

    def remove_file(self, filename_list, verbose=False):
        """
        Removes alignment objects based on their name
        :param filename_list: list with the names of the alignment objects to
        be removed
        :param verbose: Boolean. True enables terminal printing
        """

        for nm in filename_list:
            self.alignment_object_list = [x for x in self.alignment_object_list
                                          if nm != x.name]

        # Updates taxa names
        self.taxa_names = self._get_taxa_list()

    def clear_files(self):
        """
        Removes all Alignment objects from the AlignmentList
        :return:
        """

        self.alignment_object_list = []

    def select_by_taxa(self, taxa_list, mode="strict", verbose=True):
        """ This method is used to selected gene alignments according to a list
         of taxa. The modes of the method include:
        - strict: The taxa of the alignment must be exactly the same as the
        specified taxa
        - inclusive: The taxa of the alignment must contain all specified taxa
        - relaxed: At least on of the specified taxa must be in the taxa of the
         alignment """

        selected_alignments = []

        if verbose is True:
            self.log_progression.write("Selecting alignments")

        # taxa_list may be a file name (string) or a list containing the name
        #  of the taxa. If taxa_list is a file name this code will parse the
        # csv file and return a list of the taxa. Otherwise, the taxa_list
        # variable remains the same.
        try:
            file_handle = open("".join(taxa_list))
            taxa_list = self.read_basic_csv(file_handle)
        except:
            pass

        for alignment_obj in self.alignment_object_list:

            alignment_taxa = alignment_obj.iter_taxa()

            # Selected only the alignments with the exact same taxa
            if mode == "strict":

                if set(taxa_list) == set(alignment_taxa):

                    selected_alignments.append(alignment_obj)

            # Selected alignments that include the specified taxa
            if mode == "inclusive":

                if set(taxa_list) - set(alignment_taxa) == set():

                    selected_alignments.append(alignment_obj)

            if mode == "relaxed":

                for taxon in taxa_list:

                    if taxon in alignment_taxa:

                        selected_alignments.append(alignment_obj)
                        continue

        return selected_alignments

    def code_gaps(self):
        """
        Wrapper for the code_gaps method of the Alignment object.
        """

        for alignment_obj in self.alignment_object_list:
            alignment_obj.code_gaps()

    def collapse(self, write_haplotypes=True, haplotypes_file="",
                 haplotype_name="Hap"):
        """
        Wrapper for the collapse method of the Alignment object. If
        write_haplotypes is True, the haplotypes file name will be based on the
        individual input file
        :param write_haplotypes: Boolean, if True, a haplotype list
        mapping the haplotype names file will be created for each individual
        input alignment.
        :param haplotype_name: String, Custom name of the haplotypes
        """

        for alignment_obj in self.alignment_object_list:
            if write_haplotypes:
                # Set name for haplotypes file
                output_file = alignment_obj.name.split(".")[0] + haplotypes_file
                alignment_obj.collapse(haplotypes_file=output_file,
                                       haplotype_name=haplotype_name)
            else:
                alignment_obj.collapse(write_haplotypes=False,
                                       haplotype_name=haplotype_name)

    def write_to_file(self, output_format, output_suffix="", interleave=False,
                      outgroup_list=[], partition_file=True):
        """ This method writes a list of alignment objects or a concatenated
         alignment into a file """

        for alignment_obj in self.alignment_object_list:
            if alignment_obj.input_format in output_format:
                try:
                    self.reverse_concatenation
                except:
                    output_file_name = alignment_obj.name.split(".")[0]\
                                       + output_suffix + "_conv"
            else:
                output_file_name = alignment_obj.name.split(".")[0] + \
                                   output_suffix
            alignment_obj.write_to_file(output_format,
                                        output_file=output_file_name,
                                        interleave=interleave,
                                        outgroup_list=outgroup_list,
                                        partition_file=partition_file)

__author__ = "Diogo N. Silva"
__copyright__ = "Diogo N. Silva"
__credits__ = ["Diogo N. Silva", "Tiago F. Jesus"]
__license__ = "GPL"
__version__ = "0.1.0"
__maintainer__ = "Diogo N. Silva"
__email__ = "o.diogosilva@gmail.com"
__status__ = "Prototype"