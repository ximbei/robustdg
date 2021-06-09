import os
import sys

# methods=['erm', 'irm', 'csd', 'rand', 'matchdg_ctr', 'matchdg_erm', 'hybrid']
methods=['matchdg_ctr', 'hybrid']
domains= ['nih', 'chex', 'kaggle']
dataset= 'chestxray'

test_domain= sys.argv[1]
metric= sys.argv[2]
# train, acc, mia, privacy_entropy, privacy_loss_attack, match_score, feat_eval
if metric in ['acc', 'match_score', 'feat_eval', 'feat_eval_rand', 'attribute_attack']:
    data_case= sys.argv[3]

if metric == 'train':
    base_script= 'python train.py --dataset chestxray --out_classes 2 --perfect_match 0 --img_c 3 --pre_trained 1 --model_name densenet121 '
    res_dir= 'results/' + str(dataset) + '/train_logs/'    

elif metric == 'mia':
    base_script= 'python test.py --dataset chestxray --out_classes 2 --perfect_match 0 --img_c 3 --pre_trained 1 --model_name densenet121 --test_metric mia --mia_sample_size 200 --mia_logit 1 --batch_size 64 '
    res_dir= 'results/'+str(dataset)+'/privacy/' 

elif metric == 'privacy_entropy':
    base_script= 'python test.py --dataset chestxray --out_classes 2 --perfect_match 0 --img_c 3 --pre_trained 1 --model_name densenet121 --test_metric privacy_entropy --mia_sample_size 200 --batch_size 64 '
    res_dir= 'results/'+str(dataset)+'/privacy_entropy/'

elif metric == 'privacy_loss_attack':
    base_script= 'python test.py --dataset chestxray --out_classes 2 --perfect_match 0 --img_c 3 --pre_trained 1 --model_name densenet121 --test_metric privacy_loss_attack --mia_sample_size 200 --batch_size 64 '
    res_dir= 'results/'+str(dataset)+'/privacy_loss/'

elif metric  == 'acc':
    base_script= 'python test.py --dataset chestxray --out_classes 2 --perfect_match 0 --img_c 3 --pre_trained 1 --model_name densenet121 --test_metric acc ' + ' --acc_data_case ' + data_case
    res_dir= 'results/' + str(dataset) + '/acc_' + str(data_case) + '/'

elif metric  == 'match_score':
    base_script= 'python test.py --dataset chestxray --out_classes 2 --perfect_match 0 --img_c 3 --pre_trained 1 --model_name densenet121 --test_metric match_score --match_func_aug_case 1' + ' --match_func_data_case ' + data_case
    res_dir= 'results/' + str(dataset) + '/match_score_' + data_case + '/'

elif metric  == 'feat_eval':
    base_script= 'python test.py --dataset chestxray --out_classes 2 --perfect_match 0 --img_c 3 --pre_trained 1 --model_name densenet121 --test_metric feat_eval --match_func_aug_case 1' + ' --match_func_data_case ' + data_case
    res_dir= 'results/' + str(dataset) + '/feat_eval_' + data_case + '/'

elif metric  == 'feat_eval_rand':
    base_script= 'python test.py --dataset chestxray --out_classes 2 --perfect_match 0 --img_c 3 --pre_trained 1 --model_name densenet121 --test_metric feat_eval --match_func_aug_case 1' + ' --match_func_data_case ' + data_case + ' --match_case 0.0 '
    res_dir= 'results/' + str(dataset) + '/feat_eval_rand_' + data_case + '/'
        
#Test Domain
curr_test_domain= test_domain
# curr_test_domain= test_domain + '_opp_trans'
# curr_test_domain= test_domain + '_trans'

res_dir=  res_dir+ curr_test_domain + '/'    
if not os.path.exists(res_dir):
    os.makedirs(res_dir)        
    
for method in methods:    

    if method == 'erm':
        script= base_script + ' --method_name erm_match --epochs 40  --lr 0.001 --match_case 0.0 --penalty_ws 0.0 '
        
    elif method == 'rand':
        script= base_script + ' --method_name erm_match --epochs 40  --lr 0.001 --match_case 0.0 --penalty_ws 10.0 '

    elif method == 'csd':
        script= base_script + ' --method_name csd --epochs 40  --lr 0.001 --match_case 0.0 --penalty_ws 0.0 --rep_dim 1024'
        
    elif method == 'irm':
        script= base_script + ' --method_name irm --epochs 40  --lr 0.001 --match_case 0.0 --penalty_irm 10.0 --penalty_s 5'
        
    elif method == 'matchdg_ctr':
        script= base_script + ' --method_name matchdg_ctr --epochs 50 --batch_size 32 --match_case 0.0 --match_flag 1  --pos_metric cos --match_func_aug_case 1 '

    elif method == 'matchdg_erm':
        script= base_script + ' --method_name matchdg_erm  --epochs 40 --lr 0.001  --match_case -1 --penalty_ws 50.0 --ctr_match_case 0.0 --ctr_match_flag 1 --ctr_match_interrupt 5 --ctr_model_name densenet121'

    elif method == 'hybrid':
        script= base_script + ' --method_name hybrid  --epochs 40 --lr 0.001  --match_case -1 --penalty_ws 1.0 --penalty_aug 50.0 --ctr_match_case 0.0 --ctr_match_flag 1 --ctr_match_interrupt 5 --ctr_model_name densenet121'    
    
    train_domains=''
    for d in domains:
        if d != test_domain:
            train_domains+= str(d) + '_trans' + ' '
    
    print('Method: ', method, ' Train Domains: ', train_domains, ' Test Domains: ', curr_test_domain)
    script= script + ' --train_domains ' + train_domains + ' --test_domains ' + curr_test_domain
    script= script + ' > ' + res_dir + str(method) + '.txt'
    os.system(script)