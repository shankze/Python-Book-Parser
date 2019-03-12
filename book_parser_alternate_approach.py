import re
import _pickle as cPickle
import logging
import argparse

#This script is not dependant on table of contents. It detects books and chapters based their titles

# Dictionary containing key and regex pattern to match the keys
pattern_dict = {
    'blank_line': re.compile(r'^\s*$'),
    'book_number': re.compile(r'(BOOK\s\w+):?\s?(.+)?'),
    'chapter_number': re.compile(r'CHAPTER\s(\w+)'),
    'epilogue_number': re.compile(r'([A-Za-z]+\sEPILOGUE):?\s?(.+)?')
}

BODY_START_CONSEC_BLANK_LINE_COUNT = 9 #Number of blank lines between table of contents and chapter 1
FOOTER_START_CONSEC_BLANK_LINE_COUNT = 9 #Number of blank lines between end of last chapter start of footer
END_OF_CHAPTER_CONSEC_BLANK_LINE_COUNT = 4 #Number of blank lines between

class Book(object):
    def __init__(self, bk_number, bk_year, chapter_list):
        self.bk_number = bk_number
        self.bk_year = bk_year
        self.chapter_list = chapter_list

        logging.info('Created book: {}'.format(self.bk_number))

class Chapter(object):
    def __init__(self, ch_index, paragraph_list):
        self.ch_index = ch_index
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


def parse_line(line):
    """
    Do a regex search against regexes defined in pattern_dict and
    return the key and match result of the first matching regex
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

def process_file(filepath):
    """
    Process file line by line.
    Input:
        filepath: location of the file to be processed
    Return:
        book_list: A list if Book objects containing chapters, paragraphs, sentences and words
    """
    book_list = []
    try:
        with open(filepath, encoding="utf8", mode='r') as file:  # open file
            header_end_found = False # True if active line is in the body section of the file(and not header)
            prev_key,book_index,chapter_index = '','',''
            paragraph_index,sentence_index,word_index = 1,1,1
            # temporary lists to store the lower level objects before adding to the higher level object
            sentence_list,paragraph_list,chapter_list,word_list = [],[],[],[]
            # I am assuming that the whole book may not be available at once. So I am going with the safe option of
            # reading a line at once. Does not load the whole file in memory
            for line in file:
                key, match = parse_line(line) # evaluates the line against regex expressions in pattern_dict
                if key == 'blank_line' and prev_key == 'blank_line':
                    consec_empty_line_count += 1 # found consecutive blank lines, increment counter
                else:
                    consec_empty_line_count = 0 # did not find consecutive blank line, so reset it to 0
                if not header_end_found:  # continue till end of header is found. no processing requirements in header
                    if consec_empty_line_count == BODY_START_CONSEC_BLANK_LINE_COUNT:
                        header_end_found = True
                else: # in book body
                    if key == 'book_number' or key == 'epilogue_number': # current line is beginning of a book
                        if chapter_list:  # also, end of previous book and its last chapter (not true for first book)
                            book_ob = Book(book_index,book_year,chapter_list)
                            # create a book object to store previous book, set its index,
                            # year and chapter list and clear chapters list
                            book_list.append(book_ob)
                            chapter_list = []
                        # get the name and index of the new book
                        book_index = match.group(1)
                        book_year = match.group(2)
                    elif key == 'chapter_number': # current line is beginning of a new chapter
                        # get chapter name
                        chapter_index = match.group(1)
                        # reset paragraph, sentence and word indices
                        paragraph_index = 1
                        sentence_index = 1
                        word_index = 1
                    elif key == 'blank_line': # current line is blank line
                        if consec_empty_line_count == FOOTER_START_CONSEC_BLANK_LINE_COUNT:
                            # 10 consecutive lines, so end of last book
                            book_ob = Book(book_index, book_year, chapter_list) # create book object for last book
                            book_list.append(book_ob) # append it to books list
                            break  # exiting the loop as processing of footer is not required
                        if word_list: # paragraph ended without a .? or ! (could be a paragraph ending with:)
                            # end the sentence and add it to the sentence list
                            sen_ob = Sentence(sentence_index, word_list)
                            sentence_list.append(sen_ob)
                            word_list = []
                        #if consec_empty_line_count == END_OF_CHAPTER_CONSEC_BLANK_LINE_COUNT and paragraph_list.__len__() > 0:
                        if consec_empty_line_count == END_OF_CHAPTER_CONSEC_BLANK_LINE_COUNT and paragraph_list:
                            # end of chapter. Create chapter object and save the chapter
                            chap_ob = Chapter(chapter_index,paragraph_list)
                            chapter_list.append(chap_ob)
                            paragraph_list = []
                        elif sentence_list:
                            #end of paragraph. add paragraph to paragraph list
                            par_ob = Paragraph(paragraph_index,sentence_list)
                            sentence_list = []
                            paragraph_list.append(par_ob)
                            paragraph_index += 1
                            sentence_index = 1
                            word_index = 1
                    else: # line with content
                        line = line.replace("’","") #  remove apostrophes from line
                        # split lines into sentences
                        sen_in_line = re.split(r'(?<!St)[.!?]', line)
                        if sen_in_line.__len__() == 1:  #line without sentence endings
                            words_in_line = re.findall(r'[\w]+',line)
                            # find words and add them to the list
                            for word in words_in_line:
                                word_index = add_word_to_list(word, word_index, word_list)
                        else: #line containing sentence endings
                            for idx, split in enumerate(sen_in_line):
                                if split:   #check to exclude multiple consecutive periods (...)
                                    words_in_line = re.findall(r'[\w]+', split)
                                    # find words and add them to the list
                                    for word in words_in_line:
                                        word_index = add_word_to_list(word, word_index, word_list)
                                    if (idx+1) < sen_in_line.__len__():
                                        # line contains end of sentence. add sentence to sentence list
                                        sen_ob = Sentence(sentence_index,word_list)
                                        sentence_list.append(sen_ob)
                                        word_list = []
                                        sentence_index += 1
                                        word_index = 1
                prev_key = key
            if not header_end_found:
                logging.error("Header end not defined")
    except FileNotFoundError as ex:
        print(ex)
    except IOError as ex:
        print(ex)
    except Exception as ex:
        print(ex)
    return book_list

def add_word_to_list(word, word_index, word_list):
    """
    Add words to word list. Increment word index
    Input:
        word: Word to be added
        word_index: Index of the word in the word list
        word_list: List of words to which the word will be added
    Return:
        word_index
    """
    word_ob = Word(word_index, word)
    word_list.append(word_ob)
    word_index += 1
    return word_index

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s:%(levelname)s:%(message)s')

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