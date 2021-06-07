import sys
import numpy as np
import argparse
import copy
import random
import json
import os
from more_itertools import chunked

import torch
from torch.autograd import grad
from torch import nn, optim
from torch.nn import functional as F
from torchvision import datasets, transforms
from torchvision.utils import save_image
from torch.autograd import Variable
import torch.utils.data as data_utils


from utils.match_function import get_matched_pairs

class BaseAlgo():
    def __init__(self, args, train_dataset, val_dataset, test_dataset, base_res_dir, run, cuda):
        self.args= args
        self.train_dataset= train_dataset['data_loader']
        if args.method_name == 'matchdg_ctr':
            self.val_dataset= val_dataset
        else:
            self.val_dataset= val_dataset['data_loader']
        self.test_dataset= test_dataset['data_loader']
        
        self.train_domains= train_dataset['domain_list']
        self.total_domains= train_dataset['total_domains']
        self.domain_size= train_dataset['base_domain_size'] 
        self.training_list_size= train_dataset['domain_size_list']
        
        self.base_res_dir= base_res_dir
        self.run= run
        self.cuda= cuda
        
        self.post_string= str(self.args.penalty_ws) + '_' + str(self.args.penalty_diff_ctr) + '_' + str(self.args.match_case) + '_' + str(self.args.match_interrupt) + '_' + str(self.args.match_flag) + '_' + str(self.run) + '_' + self.args.pos_metric + '_' + self.args.model_name
        
        self.phi= self.get_model()
        self.opt= self.get_opt()
        self.scheduler = torch.optim.lr_scheduler.StepLR(self.opt, step_size=25)    
        
        self.final_acc=[]
        self.val_acc=[]
        self.train_acc=[]
        
        if self.args.method_name == 'dp_erm':
            self.privacy_engine= self.get_dp_noise()
    
    def get_model(self):
        
        if self.args.model_name == 'lenet':
            from models.lenet import LeNet5
            if self.args.method_name in ['csd', 'matchdg_ctr']:
                fc_layer=0
            else:
                fc_layer= self.args.fc_layer                        
            phi= LeNet5(fc_layer)

        if self.args.model_name == 'slab':
            from models.slab import SlabClf
            if self.args.method_name in ['csd', 'matchdg_ctr']:
                fc_layer=0
            else:
                fc_layer= self.args.fc_layer
            phi= SlabClf(self.args.slab_data_dim, self.args.out_classes, fc_layer)
            
        if self.args.model_name == 'fc':
            from models.fc import FC
            if self.args.method_name in ['csd', 'matchdg_ctr']:
                fc_layer=0
            else:
                fc_layer= self.args.fc_layer
            phi= FC(self.args.out_classes, fc_layer)
            
        if self.args.model_name == 'domain_bed_mnist':
            from models.domain_bed_mnist import DomainBed
            if self.args.method_name in ['csd', 'matchdg_ctr']:
                fc_layer=0
            else:
                fc_layer= self.args.fc_layer                        
            phi= DomainBed(self.args.img_c, fc_layer)
            
        if self.args.model_name == 'alexnet':
            from models.alexnet import alexnet
            if self.args.method_name in ['csd', 'matchdg_ctr']:
                fc_layer=0
            else:
                fc_layer= self.args.fc_layer            
            phi= alexnet(self.args.model_name, self.args.out_classes, fc_layer, 
                            self.args.img_c, self.args.pre_trained, self.args.os_env)
            
        if 'resnet' in self.args.model_name:
            from models.resnet import get_resnet
            if self.args.method_name in ['csd', 'matchdg_ctr']:
                fc_layer=0
            else:
                fc_layer= self.args.fc_layer
            phi= get_resnet(self.args.model_name, self.args.out_classes, fc_layer, 
                            self.args.img_c, self.args.pre_trained, self.args.os_env)
            
        if 'densenet' in self.args.model_name:
            from models.densenet import get_densenet
            if self.args.method_name in ['csd', 'matchdg_ctr']:
                fc_layer=0
            else:
                fc_layer= self.args.fc_layer
            phi= get_densenet(self.args.model_name, self.args.out_classes, fc_layer, 
                            self.args.img_c, self.args.pre_trained, self.args.os_env)
            
        print('Model Architecture: ', self.args.model_name)
        phi=phi.to(self.cuda)
        return phi
    
    def save_model(self):
        # Store the weights of the model
        torch.save(self.phi.state_dict(), self.base_res_dir + '/Model_' + self.post_string + '.pth')
        
        # Store the validation, test loss over the training epochs
        np.save( self.base_res_dir + '/Val_Acc_' + self.post_string + '.npy', np.array(self.val_acc) )
        np.save( self.base_res_dir + '/Test_Acc_' + self.post_string + '.npy', np.array(self.final_acc))
    
    def get_opt(self):
        if self.args.opt == 'sgd':
            opt= optim.SGD([
                         {'params': filter(lambda p: p.requires_grad, self.phi.parameters()) }, 
                ], lr= self.args.lr, weight_decay= self.args.weight_decay, momentum= 0.9,  nesterov=True )        
        elif self.args.opt == 'adam':
            opt= optim.Adam([
                        {'params': filter(lambda p: p.requires_grad, self.phi.parameters())},
                ], lr= self.args.lr)
        
        return opt

    
    def get_match_function(self, inferred_match, phi):
        
        data_matched, domain_data, _= get_matched_pairs( self.args, self.cuda, self.train_dataset, self.domain_size, self.total_domains, self.training_list_size, phi, self.args.match_case, self.args.perfect_match, inferred_match )
                
#         #Start initially with randomly defined batch; else find the local approximate batch
#         if epoch > 0:                    
#             inferred_match=1
#             if self.args.match_flag:
#                 data_matched, domain_data, _= get_matched_pairs( self.args, self.cuda, self.train_dataset, self.domain_size, self.total_domains, self.training_list_size, self.phi, self.args.match_case, perfect_match, inferred_match )
#             else:
#                 temp_1, temp_2, _= get_matched_pairs( self.args, self.cuda, self.train_dataset, self.domain_size, self.total_domains, self.training_list_size, self.phi, self.args.match_case, perfect_match, inferred_match )                
#         else:
#             inferred_match=0
#             data_matched, domain_data, _= get_matched_pairs( self.args, self.cuda, self.train_dataset, self.domain_size, self.total_domains, self.training_list_size, self.phi, self.args.match_case, perfect_match, inferred_match )
        
        
        # Randomly Shuffle the list of matched data indices and divide as per batch sizes
        random.shuffle(data_matched)
        data_matched= list(chunked(data_matched, self.args.batch_size))
        
        return data_matched, domain_data

    def get_match_function_batch(self, batch_idx):
        curr_data_matched= self.data_matched[batch_idx]
        curr_batch_size= len(curr_data_matched)

        data_match_tensor=[]
        label_match_tensor=[]
        for idx in range(curr_batch_size):
            data_temp=[]
            label_temp= []
            for d_i in range(len(curr_data_matched[idx])):
                key= random.choice( curr_data_matched[idx][d_i] )
                data_temp.append(self.domain_data[d_i]['data'][key])
                label_temp.append(self.domain_data[d_i]['label'][key])
            
            data_match_tensor.append( torch.stack(data_temp) )
            label_match_tensor.append( torch.stack(label_temp) )                    

        data_match_tensor= torch.stack( data_match_tensor ) 
        label_match_tensor= torch.stack( label_match_tensor )
#         print('Shape: ', data_match_tensor.shape, label_match_tensor.shape)
        return data_match_tensor, label_match_tensor, curr_batch_size
    
    def get_test_accuracy(self, case):
        
        #Test Env Code
        test_acc= 0.0
        test_size=0
        if case == 'val':
            dataset= self.val_dataset
        elif case == 'test':
            dataset= self.test_dataset

        for batch_idx, (x_e, y_e ,d_e, idx_e, obj_e) in enumerate(dataset):
            with torch.no_grad():
                x_e= x_e.to(self.cuda)
                y_e= torch.argmax(y_e, dim=1).to(self.cuda)

                #Forward Pass
                out= self.phi(x_e)                
                
                test_acc+= torch.sum( torch.argmax(out, dim=1) == y_e ).item()
                test_size+= y_e.shape[0]

        print(' Accuracy: ', case, 100*test_acc/test_size )         
        
        return 100*test_acc/test_size
    
    def get_dp_noise(self):
        
        print('Privacy Engine')
        print('Total Domains: ', self.total_domains, ' Domain Size ', self.domain_size, ' Batch Size ', self.args.batch_size)
        
        from opacus.dp_model_inspector import DPModelInspector
        from opacus.utils import module_modification
        
        inspector = DPModelInspector()        
        print(self.phi)
        self.phi = module_modification.convert_batchnorm_modules(self.phi)
        print(self.phi)
        inspector.validate(self.phi)
        
        MAX_GRAD_NORM = 1.2
        EPSILON = 50.0
        NOISE_MULTIPLIER = .38
        DELTA = 1.0/(self.total_domains*self.domain_size)
        BATCH_SIZE = self.args.batch_size
        VIRTUAL_BATCH_SIZE = 2*BATCH_SIZE
        assert VIRTUAL_BATCH_SIZE % BATCH_SIZE == 0 # VIRTUAL_BATCH_SIZE should be divisible by BATCH_SIZE
        N_ACCUMULATION_STEPS = int(VIRTUAL_BATCH_SIZE / BATCH_SIZE)        
        SAMPLE_RATE = BATCH_SIZE /(self.total_domains*self.domain_size)
        
        print(f"Using sigma={NOISE_MULTIPLIER} and C={MAX_GRAD_NORM}")
    
        from opacus import PrivacyEngine        
#         privacy_engine = PrivacyEngine(
#             self.phi,
#             sample_rate=SAMPLE_RATE * N_ACCUMULATION_STEPS,
#             alphas=[1 + x / 10.0 for x in range(1, 100)] + list(range(12, 64)),
#             noise_multiplier=NOISE_MULTIPLIER,
#             max_grad_norm=MAX_GRAD_NORM,
#         )
        privacy_engine = PrivacyEngine(
            self.phi,
            sample_rate=SAMPLE_RATE * N_ACCUMULATION_STEPS,
            noise_multiplier=NOISE_MULTIPLIER,
            max_grad_norm=MAX_GRAD_NORM,
        )
    
        privacy_engine.attach(self.opt)
        return privacy_engine