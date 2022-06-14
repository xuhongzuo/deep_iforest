"""
running DIF on Multi-variate time-series data
Please note that MSL and SMAP contain multiple entities, and thus we report the average performance over all the entities,
as has been done in many related studies.
"""

import os
import argparse
import time
import numpy as np
import utils
from config import get_algo_config, get_algo_class


dataset_root = 'data/'


parser = argparse.ArgumentParser()
parser.add_argument("--runs", type=int, default=1,
                    help="how many times we repeat the experiments to obtain the average performance")
parser.add_argument("--input_dir", type=str, default='time-series/',
                    help="not use here for ts data")
parser.add_argument("--output_dir", type=str, default='&ts_record/',
                    help="the output file path")
parser.add_argument("--dataset", type=str, default='MSL', choices=['MSL'])
parser.add_argument("--entities", type=str,
                    # default='FULL',
                    default='P-15',
                    help='FULL represents all the csv file in the folder, or a list of entity names split by comma')
parser.add_argument("--model", type=str, default='eif', choices=['dif', 'eif', 'lesinn', 'iforest'], help="")
parser.add_argument("--note", type=str, default='')

parser.add_argument('--seq_len', type=int, default=100)
parser.add_argument('--stride', type=int, default=1)
args = parser.parse_args()

model_class = get_algo_class(args.model)
model_configs = get_algo_config(args.model)



if args.model == 'dif':
    ts_model_configs={
        'batch_size': 10000,
        'layers': 1,
        'hidden_dim': 20,
    }
    model_configs = dict(model_configs, **ts_model_configs)
    model_configs['data_type'] = 'ts'
    model_configs['network_name'] = 'gru'
print(model_configs)



# create and print results file header
os.makedirs(args.output_dir, exist_ok=True)
cur_time = time.strftime("%m-%d %H.%M.%S", time.localtime())
result_file = os.path.join(args.output_dir, f'{args.model}_{args.dataset}_results.csv')

f = open(result_file, 'a')
print(cur_time, file=f)
print('\n---------------------------------------------------------', file=f)
print(f'model: {args.model}, data dir: {args.input_dir}, dataset: {args.dataset}, {args.runs}runs, ', file=f)
for k in model_configs.keys():
    print(f'Parameters,\t [{k}], \t\t  {model_configs[k]}', file=f)
print(f'args,\t [seq_len], \t\t  {args.seq_len}', file=f)
print(f'args,\t [stride], \t\t  {args.stride}', file=f)
print(f'Note: {args.note}', file=f)
print(f'---------------------------------------------------------', file=f)
print(f'data, adj_auroc, std, adj_ap, std, adj_f1, std, adj_p, std, adj_r, std, time, model', file=f)
f.close()


train_df_lst, test_df_lst, label_lst, name_lst = utils.get_data_lst_ts(os.path.join(dataset_root, args.input_dir),
                                                                       args.dataset, entities=args.entities)
print(name_lst)
for train_df, test_df, labels, dataset_name in zip(train_df_lst, test_df_lst, label_lst, name_lst):
    x_train = train_df.values
    x_test = test_df.values

    entries = []
    t_lst = []
    for i in range(args.runs):
        start_time = time.time()
        print(f'\nRunning [{i+1}/{args.runs}] of [{args.model}] on Dataset [{dataset_name}]')

        clf = model_class(**model_configs, random_state=42+i)

        x = np.concatenate([x_train, x_test])
        if args.model == 'dif':
            x_seq = utils.get_sub_seqs(x, seq_len=args.seq_len, stride=args.stride)
            x_test_seq = utils.get_sub_seqs(x_test, seq_len=args.seq_len, stride=1)
            clf.fit(x_seq)
            scores = clf.decision_function(x_test_seq)

            padding_list = np.zeros(args.seq_len-1)
            scores = np.hstack([padding_list, scores])
        else:
            clf.fit(x)
            scores = clf.decision_function(x_test)

        entry = utils.eval_ts(scores=scores, labels=labels, test_df=test_df)
        entries.append(entry)
        print(dataset_name, end=', ')
        for e in entry:
            print(e, end=', ')
        print()

        t = round(time.time() - start_time, 1)
        t_lst.append(t)

    avg_entry = np.average(np.array(entries), axis=0)
    std_entry = np.std(np.array(entries), axis=0)

    f = open(result_file, 'a')
    txt = '%s, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, ' \
          '%.4f, %.4f, %.4f, %.4f, %.1f, %s ' % (dataset_name,
                                                 avg_entry[0], std_entry[0], avg_entry[1], std_entry[1],
                                                 avg_entry[2], std_entry[2], avg_entry[3], std_entry[3],
                                                 avg_entry[4], std_entry[4],
                                                 np.average(t_lst),  args.model)
    print(txt)
    print(txt, file=f)
    f.close()


