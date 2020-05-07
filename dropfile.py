import argparse
import time
import preprocessing
import numpy as np
from collections import defaultdict
# cosine similarity
def cosine_similarity(A,B):
  ndA = np.asarray(A)
  ndB = np.asarray(B)
  return np.dot(ndA,ndB)/(np.linalg.norm(ndA)*np.linalg.norm(ndB))


# main body of program: DropFile
# input : input file path, root path 
# output : recommended path
def dropfile(input_file: str, root_path: str, DTM=None, vocab=None):
  # preprocessing : lookup hierarchy of root path
  directory_dict = defaultdict(list) # empty dictionary for lookup_directory function
  dir_hierarchy = preprocessing.lookup_directory(root_path, directory_dict) # change it to have 2 parameter

  file_list = list()
  dir_list = list()
  label_num = 0
  for tar_dir in dir_hierarchy:
    file_list += dir_hierarchy[tar_dir]
    dir_list.append(tar_dir)
    label_num += 1
    
  # preprocessing : build vocabulary from file_list
  if (DTM is None) and (vocab is None):
    doc_list = list()
    for file in file_list:
      doc_list.append(preprocessing.file2tok(file))
    vocab = preprocessing.build_vocab(doc_list)
    # preprocessing : build DTM of files under root_path
    DTM = preprocessing.build_DTM(doc_list, vocab)
    
  # preprocessing : build BoW, DTM score of input file
  dtm_vec = preprocessing.build_DTMvec(input_file, vocab)
  # similarity calculation using cosine similarity
  sim_vec = list()
  for i in range(len(DTM)):
    sim_vec.append(cosine_similarity(DTM[i],dtm_vec))
  # calculate label score
  # result will be score of each directory
  label_score = [0.0 for i in range(label_num)]
  offset = 0
  for label, tar_dir in enumerate(dir_list):
    file_num = len(dir_hierarchy[tar_dir])
    for j in range(file_num):
      label_score[label] += sim_vec[offset+j]
    label_score[label] /= file_num
    offset += file_num
  
  # find directory that has maximum score
  dir_path = dir_list[label_score.index(max(label_score))]
  return dir_path, DTM, vocab


# main execution command
if __name__=='__main__':
  parser = argparse.ArgumentParser(description='dropFile program')
  parser.add_argument('-r', '--root-path', help='root path that input file should be classified into',
                      type=str, action='store', default='./test')
  parser.add_argument('-i', '--input-file', help='input file initial path',
                      type=str, action='store')
  args = parser.parse_args()
  print('root path : {}, input file: {}'.format(args.root_path, args.input_file))
  if (args.input_file is None):
    parser.error("--input-file(-i) format should be specified")
  
  print("Running DropFile...")
  start = time.time()
  recommendation_path = dropfile(args.input_file, args.root_path)
  print("elapsed time: {}sec".format(time.time()-start))
  print("Execution Result: {}".format(recommendation_path))