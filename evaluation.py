# evaluation code
import argparse
import os
import os.path
import random
import shutil
from preprocessing.preprocessing import Preprocessing
import dropfile
from tqdm import tqdm
import time # add time module
from collections import defaultdict
from itertools import combinations, product, chain
import sys
import seaborn as sn
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.figure as fig
preprocessing = Preprocessing()
# import naivebayes
import spacy
import pickle

INITIAL_TEST_FRAC = 0.8
INITIAL_PATH = './test'

# function : prepare environment, build new root_path and relocate each file
# input : file_list, locate_flag
#         ex) file_list : ["/test/nlp-1.pdf","/test/nlp-2.pdf",...]
#             locate_flag : [true,false,true,true, ...] 
#                (= 해당 인덱스의 파일이 initial로 존재할지, 혹은 test용
#                  input으로 사용될지에 대한 flag)
# output : test_path (test가 진행될 root_path, 새로운 디렉토리에 re-locate시켜주어야함.
#                     test 디렉토리에서 locate_flag가 true인 것들에 대해서만 새로운 root_path(e.g. /eval 디렉토리)로 복사해주어야함)
#          label (test의 input으로 들어갈 파일들에 대한 올바른 결과값에 대한 리스트)
#          testset (test에 사용될 파일들의 절대경로 리스트, e.g. ["/test/nlp-1.pdf",..], 원래 파일들이 있었던 경로로 지정)
# implementation : os 라이브러리 사용
def prepare_env(comb_num: int, file_list: list, locate_flag: list):
  current_path = os.getcwd()
  test_path = current_path + "/eval-{}/".format(comb_num)

  label = ["" for _ in range(len(file_list))]

  find_common_parent_dir = []
  if test_path in os.listdir(current_path):
    shutil.rmtree(test_path)
  if test_path not in os.listdir(current_path):
    os.makedirs(test_path, exist_ok=True)

  try:
    # 가장 상위의 공통 디렉토리를 찾는다.
    for file_name in file_list:
      find_common_parent_dir.append(os.path.split(file_name)[0].split("/"))  # \n이나 /를 기준으로 자른다

    compare_dir = find_common_parent_dir[0]
    for temp_dir in find_common_parent_dir[1:]:
      if len(compare_dir) < len(temp_dir):
        continue
      elif len(compare_dir) == len(temp_dir):
        if compare_dir[-1] != temp_dir[-1]:
          compare_dir = compare_dir[:-1]
        else:
          continue
      else:
        compare_dir = temp_dir

    # 가장 상위의 공통 디렉토리
    common_parent_dir = "/".join(compare_dir)

    for idx, file_name in enumerate(file_list):
      file_dir = os.path.split(file_name)[0]
      # 파일이 common_parent_dir보다 하위 디렉토리에 있다면, 하위 디렉토리들을 생성한 후 copy
      if file_dir != common_parent_dir:
        a = file_dir.split("/")
        b = common_parent_dir.split("/")
        additional_path = a[len(b):]
        temp_path = test_path[:-1]
        
        for i in range(len(additional_path)):
          subdir = temp_path + "/" + additional_path[i]
          if additional_path[i] not in os.listdir(temp_path):
            os.makedirs(subdir,exist_ok=True)
          temp_path = subdir

        label[idx] = subdir
        
        if locate_flag[idx]:
          shutil.copy2(file_name, subdir)
      else:
        shutil.copy2(file_name, test_path)
        label[idx] = test_path

  except PermissionError:
    pass
  
  true_label = list()
  testset = list()
  for idx, flag in enumerate(locate_flag):
    if not flag:
      testset.append(file_list[idx])
      true_label.append(label[idx])
  return test_path, true_label, testset


# function : evaluation이 이루어질 모든 경우의 location_flag 리스트를 구한다
# input : file_list
# output : list of locate_flag
# implementation : output의 각 element는 위 prepare_env 함수의 locate_flag로 들어갈 수 있는 포맷이어야함
def calculate_combination(file_list):
  lf_list = list()
  length = len(file_list)
  l1 = int(length/4)
  l2 = l1*2
  l3 = l1*3
  lf_list.append([True]*l3 + [False]*l1)
  lf_list.append([True]*l2 + [False]*l1 + [True]*l1)
  lf_list.append([True]*l1+[False]*l1+[True]*l2)
  lf_list.append([False]*l1+ [True]*l3)
  return lf_list


# evaluate for experiment
def evaluation(root_path: str, preprocessing_name: str, score_name: str, interim_flag: bool):
  # load the spacy language model
  # nlp = spacy.load("en_core_web_lg")
  # preprocessing : lookup hierarchy of root path
  pickle_path = root_path + "-pickle"
  if pickle_path not in os.listdir('.'):
    os.makedirs(pickle_path, exist_ok=True)
  directory_dict = defaultdict(list) # empty dictionary for lookup_directory function
  dir_hierarchy = preprocessing.lookup_directory(root_path, directory_dict)
  file_list = list()
  dir_list = list()
  label_num = 0
  for tar_dir in dir_hierarchy:
    file_list += dir_hierarchy[tar_dir]
    dir_list.append(tar_dir)
    label_num += 1
  random.shuffle(file_list)
  
  # making directory name list
  directory_name = [path.split('/')[-1].split('\\')[-1] for path in dir_list]  # OS dependency
  
  # calculate combination
  print("Calculating Evaluation combination..")
  combination = calculate_combination(file_list)

  # start evaluation
  print("Start evaluation..")
  
  if interim_flag:
    conf_mat = [[0 for _ in range(len(dir_list))] for _ in range(len(dir_list))] # 3x3 or 4x4 confusion matrix

  case3_file_list = './test/pl'
  trial = 0
  correct = 0
  total_len = len(combination)
  for i,locate_flag in enumerate(combination):
    print("locate_flag is : ", locate_flag)
    local_correct = 0
    print("="*50)
    print("evaluating combination set {}/{}".format(i,total_len))
    # create test environment
    test_path, label, testset = prepare_env(i+1,file_list,locate_flag)
    if root_path == './test/case3':
      with open('./test/case1-pickle/DTM-0', 'rb') as f:
        DTM = pickle.load(f)
      with open('./test/case1-pickle/vocab-0', 'rb') as f:
        vocab = pickle.load(f)
      with open('./test/case1-pickle/synonym_dict-0', 'rb') as f:
        synonym_dict = pickle.load(f)
      file_list = os.listdir(case3_file_list)
      for input_path in file_list:
        input_path = case3_file_list + '/' + input_path
        answer,_,_,_ = dropfile.dropfile(input_path,test_path,DTM,vocab,synonym_dict,preprocessing=preprocessing_name,scoring=score_name)
      return
    vocab = None
    DTM = None
    synonym_dict = None
    for j,input_path in enumerate(tqdm(testset,desc="evaluation",mininterval=1)):
      print("input_path is : ", input_path)
      answer_name = ""
      label_name = ""
      trial +=1
      # case3 (case1을 가져와서 새로운 file 넣기(score가 일정해야함))
      if root_path == './test/case3':
        with open('./test/case1-pickle/DTM-{}'.format(i), 'rb') as f:
          DTM = pickle.load(f)
        with open('./test/case1-pickle/vocab-{}'.format(i), 'rb') as f:
          vocab = pickle.load(f)
        with open('./test/case1-pickle/synonym_dict-{}'.format(i), 'rb') as f:
          synonym_dict = pickle.load(f)

      elif os.path.isfile(pickle_path+'/DTM-{}'.format(i)):
        with open(pickle_path + '/DTM-{}'.format(i), 'rb') as f:
          DTM = pickle.load(f)
        with open(pickle_path + '/vocab-{}'.format(i), 'rb') as f:
          vocab = pickle.load(f)
        with open(pickle_path + '/synonym_dict-{}'.format(i), 'rb') as f:
          synonym_dict = pickle.load(f)

      if (vocab is None) and (DTM is None) and (synonym_dict is None):
        answer, DTM, vocab, synonym_dict = dropfile.dropfile(input_path,test_path,preprocessing=preprocessing_name,scoring=score_name)
        with open(pickle_path + '/DTM-{}'.format(i), 'wb') as f:
          pickle.dump(DTM, f)
        with open(pickle_path + '/vocab-{}'.format(i), 'wb') as f:
          pickle.dump(vocab, f)
        with open(pickle_path + '/synonym_dict-{}'.format(i), 'wb') as f:
          pickle.dump(synonym_dict, f)
        # answer, DTM, vocab = naivebayes.dropfile_bayes(input_path, test_path)

      else:
        answer,_,_,_ = dropfile.dropfile(input_path,test_path,DTM,vocab,synonym_dict,preprocessing=preprocessing_name,scoring=score_name)
        # answer,_,_ = naivebayes.dropfile_bayes(input_path, test_path, DTM, vocab, synonym_dict)

      if (answer==label[j]):
        correct += 1
        local_correct += 1
        if interim_flag:
          answer_name = answer.split('/')[-1].split('\\')[-1]
          direct_idx = directory_name.index(answer_name)
          conf_mat[direct_idx][direct_idx] += 1

      else:
        if interim_flag:
          answer_name = answer.split('/')[-1].split('\\')[-1]  # OS dependency
          label_name = label[j].split('/')[-1].split('\\')[-1]  # OS dependency
          orig_idx = directory_name.index(label_name)
          direct_idx = directory_name.index(answer_name)
          conf_mat[orig_idx][direct_idx] += 1
        
    # delete test environment
    shutil.rmtree(test_path)
    print("iteration-{}: {}/{} correct".format(i+1,local_correct,len(testset)))
  print("Evaluation Result: {}/{}".format(correct,trial))
  

  df_cm = pd.DataFrame(conf_mat, index = directory_name, columns = directory_name)
  sn.set(font_scale=1.4) # for label size
  fig, ax = plt.subplots(figsize=(8,8))
  sn.heatmap(df_cm, annot=True, annot_kws={"size": 12}, ax=ax) # font size
  ax.set_xlabel('expected directory')
  ax.set_ylabel('recommended directory')
  ax.set_title('result')
  plt.savefig('confusion_matrix_{}.png'.format(root_path.split('/')[-1]))
  plt.show()
  
  


# main execution command
if __name__=='__main__':
  parser = argparse.ArgumentParser(description='dropFile evaluation program')
  parser.add_argument('-r', '--root-path', help='root path that input file should be classified into',
                      type=str, action='store', default='./test/case2-3')
  parser.add_argument('-e', help='experiment option for interim report', default=True, action='store_true')
  parser.add_argument('-a', help='name of preprocessing ', type=str, default=None, action='store')
  parser.add_argument('-b', help='name of score ', type=str, default=None, action='store')
  args = parser.parse_args()

  print("Running Evaluation DropFile...")
  start = time.time()
  evaluation(args.root_path, args.a, args.b, args.e)
  print("elapsed time: {}sec".format(time.time()-start))