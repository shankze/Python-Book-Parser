import re
import _pickle as cPickle
import logging
import argparse

#This script parses a book based on the Table of Contents.

# Dictionary containing key and regex pattern to match the keys
pattern_dict = {
    'blank_line': re.compile(r'^\s*$'),
    'contents': re.compile(r'^\s{4}CONTENTS\n$')
}

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s:%(levelname)s:%(message)s')

BODY_START_CONSEC_BLANK_LINE_COUNT = 9 #Number of blank lines between table of contents and chapter 1
FOOTER_START_CONSEC_BLANK_LINE_COUNT = 9 #Number of blank lines between end of last chapter start of footer
END_OF_CHAPTER_CONSEC_BLANK_LINE_COUNT = 4 #Number of blank lines between

class Book(object):
    def __init__(self, bk_number, bk_year):
        self.bk_number = bk_number
        self.bk_year = bk_year

    def add_chapter_list(self,chapter_list):
        self.chapter_list = chapter_list

        logging.info('Created book: {}'.format(self.bk_number))

class Chapter(object):
    def __init__(self, ch_index):
        self.ch_index = ch_index

    def add_paragraph_list(self,paragraph_list):
        self.paragraph_list = paragraph_list


class Paragraph(object):
    def __init__(self, p_index, sentence_list):
        self.p_index = p_index
        self.sentence_list = sentence_list

class Sentence(object):
    def __init__(self, s_index,wordObj_list):
        self.s_index = s_index
        self.wordObj_list = wordObj_list


class Word(object):
    def __init__(self, w_index, word):
        self.w_index = w_index
        self.word = word

class ToCItem(object):
    def __init__(self, name,type):
        self.name = name
        self.type = type

    def add_year(self,year):
        self.year = year

def parse_line(line):
    """
    Do a regex search against regexes defined in pattern_dict and
    return the key and match result of the first matching regex
    :param line: line to process
    :return:
        key: matching key
        match: match
    """
    for key, rx in pattern_dict.items():
        match = rx.search(line)
        if match:
            return key, match
    # if there are no matches
    return None, None


def obj_dict(obj):
    """
    Default method to serialize objects json.dump cannor serialize
    """
    return obj.__dict__

def parse_book_name(line):
    """
    Extracts book name and year from title
    :param line: string containing book title
    :return:
        name: book name
        year: book year
    """
    parts = line.split(':')
    name = parts[0].strip()
    if(parts.__len__() > 1):
        year = parts[1].strip()
    else:
        year = 'Unknown'
    return name, year


def process_file(filepath):
    """
    Process file line by line.
    :param filepath: location of the file to be processed
    :return:
        book_list: A list if Book objects containing chapters, paragraphs, sentences and words
    """
    book_list = []
    try:
        with open(filepath, encoding="utf8", mode='r') as file:  # open file
            # in_body: True if current line is in book body
            # in_toc: True if current line is in table of contents
            in_body,in_toc = False, False
            prev_key,book_index,chapter_index,next_itemn_type = '','','',''
            # temporary lists to store the lower level objects before adding to the higher level object
            sentence_list,paragraph_list,chapter_list,word_list, toc_list = [],[],[],[],[]
            toc_index = 0 # counter for tracking items in toc_list
            # I am assuming that the whole book may not be available at once. So I am going with the safe option of
            # reading a line at once. Does not load the whole file in memory
            for line in file:
                key, match = parse_line(line) # evaluates the line against regex expressions in pattern_dict
                if key == 'blank_line' and prev_key == 'blank_line':
                    consec_empty_line_count += 1 # found consecutive blank lines, increment counter
                else:
                    consec_empty_line_count = 0 # did not find consecutive blank line, so reset it to 0
                if not in_body:  # continue till table of contents is found. no processing requirements in header
                    if key == 'contents':
                        in_toc = True # active line is first line of table of contents
                    elif in_toc: # in table of contents
                        if consec_empty_line_count == BODY_START_CONSEC_BLANK_LINE_COUNT:
                            in_body = True # end of Table of Contents. In body
                        elif key == 'blank_line':
                            if consec_empty_line_count == 1:
                                next_itemn_type = 'b' # found 2 blank lines, so next line should be a book title
                            elif consec_empty_line_count == 0:
                                next_itemn_type = 'c' # found 1 blank line, so next line should be a chapter title
                        else:
                            if next_itemn_type == 'b':
                                # found book title. extract name and year. add it to toc list
                                bk_name,bk_year = parse_book_name(line)
                                tocItem = ToCItem(bk_name,'b')
                                tocItem.add_year(bk_year)
                                toc_list.append(tocItem)
                            else:
                                # found chapter title. extract name and year. add it to toc list
                                tocItem = ToCItem(line.strip(), 'c')
                                toc_list.append(tocItem)
                else: # in book body
                    if toc_list[toc_index].name in line:
                        # current line matches the next title in table of contents list
                        if toc_list[toc_index].type == 'b':
                            # matching title is book title
                            if chapter_list:
                                # end of last book. add its chapter list and add it to the book_list
                                try:
                                    book_ob.add_chapter_list(chapter_list)
                                    book_list.append(book_ob)
                                except Exception:
                                    logging.error("One or more books in the table of contents were not found in the body of the book")
                                    logging.error("It will not be added to the output")
                                    logging.error("Please verify the output")
                            # create a new book item with the title and year for current book title
                            book_ob = Book(toc_list[toc_index].name,toc_list[toc_index].year)
                            chapter_list = []
                            paragraph_list = []
                            # check to ensure we do not go past the length of table of contents list
                            if toc_index + 1 < toc_list.__len__():
                                toc_index += 1
                        elif toc_list[toc_index].type == 'c':
                            # matching title is chapter title. create chapter object
                            chap_ob = Chapter(toc_list[toc_index].name)
                            paragraph_list = []
                            if toc_index + 1 < toc_list.__len__():
                                toc_index += 1
                    elif key == 'blank_line': # current line is blank line
                        if consec_empty_line_count == FOOTER_START_CONSEC_BLANK_LINE_COUNT:
                            # 10 consecutive lines, so end of last book
                            book_ob.add_chapter_list(chapter_list)
                            book_list.append(book_ob) # append it to books list
                            break  # exiting the loop as processing of footer is not required
                        elif consec_empty_line_count == END_OF_CHAPTER_CONSEC_BLANK_LINE_COUNT and paragraph_list:
                            # end of chapter. add the paragraph list to the current chapter object
                            # add the chapter object to the current chapter list
                            try:
                                chap_ob.add_paragraph_list(paragraph_list)
                                chapter_list.append(chap_ob)
                            except Exception:
                                logging.error("One or more chapters in the table of contents were not found in the body of the book")
                                logging.error("The following chapter was not found: " + toc_list[toc_index].name)
                                logging.error("It will not be added to the output")
                                if toc_index + 1 < toc_list.__len__():
                                    toc_index += 1
                            paragraph_list = []
                        # single empty line in body means end of paragraph
                        if word_list: # paragraph ended without the sentence ending
                            # i.e. paragraph ended with ':'
                            # end the sentence and add it to the sentence list
                            sen_ob = Sentence(sentence_list.__len__() + 1, word_list)
                            sentence_list.append(sen_ob)
                            word_list = []
                        if sentence_list:
                            #end of paragraph. create paragraph object and add it to paragraph list
                            par_ob = Paragraph(paragraph_list.__len__() + 1,sentence_list)
                            sentence_list = []
                            paragraph_list.append(par_ob)
                    else: # current line has content (in body, not a title and not blank)
                        line = line.replace("’","") # remove apostrophes
                        # split lines if they contain '.','?' or '!'. they contain sentence ending punctuations
                        sen_in_line = re.split(r'(?<!St)[.!?]', line)
                        if sen_in_line.__len__() == 1:  # line without sentence endings
                            words_in_line = re.findall(r'[\w]+',line)
                            # find words and add them to the list
                            for word in words_in_line:
                                add_word_to_list(word, word_list)
                        else: # line containing sentence endings
                            for idx, split in enumerate(sen_in_line):
                                if split:   # check to exclude multiple consecutive periods (...)
                                    words_in_line = re.findall(r'[\w]+', split)
                                    # find words and add them to the list
                                    for word in words_in_line:
                                        add_word_to_list(word, word_list)
                                    if (idx+1) < sen_in_line.__len__():
                                        # line contains end of sentence. add sentence to sentence list
                                        sen_ob = Sentence(sentence_list.__len__() + 1,word_list)
                                        sentence_list.append(sen_ob)
                                        word_list = []
                prev_key = key
    except FileNotFoundError as ex:
        print(ex)
    except IOError as ex:
        print(ex)
    except Exception as ex:
        logging.exception(ex)
    return book_list


def add_word_to_list(word, word_list):
    """
    Add words to word list. Increment word index
    :param word: Word to be added
    :param word_list: List of words to which the word will be added
    :return:
    """
    word_ob = Word(word_list.__len__() + 1, word)
    word_list.append(word_ob)


def main_wrapper(args):
    """
    :param args:
    :return:
    """
    inp_filepath = args.input_file_path
    out_filepath = args.output_file_path

    logging.info('Working on book: {}'.format(inp_filepath))
    book_list = process_file(inp_filepath)

    if book_list:
        try:
            with open(out_filepath,mode='wb') as cpickle_file:
                cPickle.dump(book_list,cpickle_file)
        except Exception as ex:
            print(ex)
    else:
        print('No books found')


def args_parser():
    """
    handles and validates CLI
    :return:
    """
    parser = argparse.ArgumentParser(description="Parses files containing books and serializes the structure")
    parser.add_argument("-inp",help="full path of the file to parse",dest = "input_file_path",type=str,required=True)
    parser.add_argument("-out", help="output path to the serialized file", dest="output_file_path", type=str, required=True)
    parser.set_defaults(func=main_wrapper)
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    args_parser()
