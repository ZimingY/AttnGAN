from __future__ import print_function
from six.moves import range

import torch
import torch.nn as nn
import torch.optim as optim
from torch.autograd import Variable
import torch.backends.cudnn as cudnn

from PIL import Image

from miscc.config import cfg
from miscc.utils import mkdir_p
from miscc.utils import build_super_images, build_super_images2
from miscc.utils import weights_init, load_params, copy_G_params
from model import G_DCGAN, G_NET
from model import D_NET64_WGAN, D_NET128_halfWGAN, D_NET256_halfWGAN, D_NET64_halfWGAN
from model import D_NET64, D_NET128, D_NET256
from datasets import prepare_data
from model import RNN_ENCODER, CNN_ENCODER
#test
from miscc.losses import words_loss, generator_loss_halfWGAN, discriminator_loss_halfWGAN
from miscc.losses import discriminator_loss, discriminator_loss_WGAN, generator_loss_WGAN_epoch, KL_loss
import os
import time
import numpy as np
import sys
from torch.autograd import Variable
from torch import autograd
class condGANTrainer(object):
    def __init__(self, output_dir, data_loader, n_words, ixtoword):
        if cfg.TRAIN.FLAG:
            self.model_dir = os.path.join(output_dir, 'Model')
            self.image_dir = os.path.join(output_dir, 'Image')
            mkdir_p(self.model_dir)
            mkdir_p(self.image_dir)

        torch.cuda.set_device(cfg.GPU_ID)
        cudnn.benchmark = True

        self.batch_size = cfg.WGAN.BATCH_SIZE_yin 
        self.max_epoch = cfg.WGAN.epoch
        self.snapshot_interval = cfg.TRAIN.SNAPSHOT_INTERVAL
        self.critic = cfg.WGAN.CRITIC

        self.n_words = n_words
        self.ixtoword = ixtoword
        self.data_loader = data_loader
        self.num_batches = len(self.data_loader)

    def build_models(self):
        # ###################encoders######################################## #
        if cfg.TRAIN.NET_E == '':
            print('Error: no pretrained text-image encoders')
            return

        image_encoder = CNN_ENCODER(cfg.TEXT.EMBEDDING_DIM)
        img_encoder_path = cfg.TRAIN.NET_E.replace('text_encoder', 'image_encoder')
        state_dict = \
            torch.load(img_encoder_path, map_location=lambda storage, loc: storage)
        image_encoder.load_state_dict(state_dict)
        for p in image_encoder.parameters():
            p.requires_grad = False
        print('Load image encoder from:', img_encoder_path)
        image_encoder.eval()

        text_encoder = \
            RNN_ENCODER(self.n_words, nhidden=cfg.TEXT.EMBEDDING_DIM)
        state_dict = \
            torch.load(cfg.TRAIN.NET_E,
                       map_location=lambda storage, loc: storage)
        text_encoder.load_state_dict(state_dict)
        for p in text_encoder.parameters():
            p.requires_grad = False
        print('Load text encoder from:', cfg.TRAIN.NET_E)
        text_encoder.eval()

        # #######################generator and discriminators############## #
        netsD = []
              
        netsD.append(D_NET64_WGAN())
        netsD.append(D_NET128())
        netsD.append(D_NET256())
            

        # netsD.append(D_NET64_halfWGAN())
        # netsD.append(D_NET128_halfWGAN())
        # netsD.append(D_NET256_halfWGAN())
            

        netG = G_NET()
        netG.apply(weights_init)

        
        for i in range(len(netsD)):
            netsD[i].apply(weights_init)
        print('# of netsD', len(netsD))
        epoch = 0

        #### ````````````````````````````````````````````````````````````````````````
        #### ````````````````````````````````````````````````````````````````````````
        #### ````````````````````````````````````````````````````````````````````````

        if cfg.TRAIN.NET_G != '':
            state_dict = \
                torch.load(cfg.TRAIN.NET_G, map_location=lambda storage, loc: storage)
            netG.load_state_dict(state_dict)
            print('Load G from: ', cfg.TRAIN.NET_G)
            istart = cfg.TRAIN.NET_G.rfind('_') + 1
            iend = cfg.TRAIN.NET_G.rfind('.')
            epoch = cfg.TRAIN.NET_G[istart:iend]

            print(epoch)

            epoch = int(epoch) + 1
            if cfg.TRAIN.B_NET_D:
                Gname = cfg.TRAIN.NET_G
                for i in range(len(netsD)):
                    s_tmp = Gname[:Gname.rfind('/')]
                    Dname = '%s/netD%d.pth' % (s_tmp, i)
                    print('Load D from: ', Dname)
                    state_dict = \
                        torch.load(Dname, map_location=lambda storage, loc: storage)
                    netsD[i].load_state_dict(state_dict)


        #### ````````````````````````````````````````````````````````````````````````
        #### ````````````````````````````````````````````````````````````````````````
        #### ````````````````````````````````````````````````````````````````````````




        text_encoder = text_encoder.cuda()
        image_encoder = image_encoder.cuda()
        netG.cuda()
        for i in range(len(netsD)):
            netsD[i].cuda()
        return [text_encoder, image_encoder, netG, netsD, epoch]

    def define_optimizers(self, netG, netsD):
        optimizersD = []
        num_Ds = len(netsD)
        for i in range(num_Ds):
            if i ==0:

                opt = optim.Adam(netsD[i].parameters(),
                                 lr=cfg.TRAIN.DISCRIMINATOR_LR * 0.05,
                                 betas=(0.5, 0.9))
                optimizersD.append(opt)
            else:
                opt = optim.Adam(netsD[i].parameters(),
                             lr=cfg.TRAIN.DISCRIMINATOR_LR * 0.1,
                             betas=(0.5, 0.999))
                optimizersD.append(opt)

        optimizerG = optim.Adam(netG.parameters(),
                                lr=cfg.TRAIN.GENERATOR_LR * 0.05,
                                betas=(0.5, 0.9))

        return optimizerG, optimizersD

    def prepare_labels(self):
        batch_size = self.batch_size
        real_labels = Variable(torch.FloatTensor(batch_size).fill_(1))
        fake_labels = Variable(torch.FloatTensor(batch_size).fill_(0))
        match_labels = Variable(torch.LongTensor(range(batch_size)))
        
        real_labels = real_labels.cuda()
        fake_labels = fake_labels.cuda()
        match_labels = match_labels.cuda()

        return real_labels, fake_labels, match_labels

    def save_model(self, netG, avg_param_G, netsD, epoch):
        backup_para = copy_G_params(netG)
        load_params(netG, avg_param_G)
        torch.save(netG.state_dict(),
            '%s/netG_epoch_%d.pth' % (self.model_dir, epoch))
        load_params(netG, backup_para)
        #
        for i in range(len(netsD)):
            netD = netsD[i]
            torch.save(netD.state_dict(),
                '%s/netD%d.pth' % (self.model_dir, i)) ##  output/birds_attn2_timestamp/model
        print('Save G/Ds models.')

    def set_requires_grad_value(self, models_list, brequires):
        
        for p in models_list.parameters():
            p.requires_grad = brequires

 
    def save_img_results(self, netG, noise, sent_emb, words_embs, mask,
                         image_encoder, captions, cap_lens,
                         gen_iterations, name='current'):
        # Save images
        fake_imgs, attention_maps, _, _ = netG(noise, sent_emb, words_embs, mask)
        for i in range(len(attention_maps)):
            if len(fake_imgs) > 1:
                img = fake_imgs[i + 1].detach().cpu()
                lr_img = fake_imgs[i].detach().cpu()
            else:
                img = fake_imgs[0].detach().cpu()
                lr_img = None
            attn_maps = attention_maps[i]
            att_sze = attn_maps.size(2)

            # print('attn_maps', attn_maps.size())

            img_set, _ = \
                build_super_images(img, captions, self.ixtoword,
                                   attn_maps, att_sze, lr_imgs=lr_img)
            if img_set is not None:
                im = Image.fromarray(img_set)
                fullpath = '%s/G_%s_%d_%d.png'\
                    % (self.image_dir, name, gen_iterations, i)
                im.save(fullpath)

        # for i in range(len(netsD)):
        i = -1
        img = fake_imgs[i].detach()
        region_features, _ = image_encoder(img)
        att_sze = region_features.size(2)

        _, _, att_maps = words_loss(region_features.detach(),
                                    words_embs.detach(),
                                    None, cap_lens,
                                    None, self.batch_size)
        # print('att_maps', att_maps.size())
        img_set, _ = \
            build_super_images(fake_imgs[i].detach().cpu(),
                               captions, self.ixtoword, att_maps, att_sze)
        if img_set is not None:
            im = Image.fromarray(img_set)
            fullpath = '%s/D_%s_%d.png'\
                % (self.image_dir, name, gen_iterations)
            im.save(fullpath)




    # def train(self):
    #     text_encoder, image_encoder, netG, netsD, start_epoch = self.build_models()
    #     avg_param_G = copy_G_params(netG)
    #     optimizerG, optimizersD = self.define_optimizers(netG, netsD)
    #     real_labels, fake_labels, match_labels = self.prepare_labels()
    #     batch_size = self.batch_size
    #     nz = cfg.GAN.Z_DIM
    #     noise = Variable(torch.FloatTensor(batch_size, nz))
    #     fixed_noise = Variable(torch.FloatTensor(batch_size, nz).normal_(0, 1))
    #     noise, fixed_noise = noise.cuda(), fixed_noise.cuda()
    #     gen_iterations = 0
    #     print('')
    #     print('''WGAN generator training %d epoch, batch size is %d, %d number of batches per epoch,
    #         models saved every %d epoch''' % (self.max_epoch,self.batch_size,self.num_batches, cfg.WGAN.SNAPSHOT_INTERVAL))
    #     print('')
    #     for epoch in range(start_epoch, self.max_epoch):
    #         start_t = time.time()
    #         data_iter = iter(self.data_loader)
    #         step = 0
    #         ##      ##.         one epoch  ##            ##
    #         while (step+self.critic+1) < self.num_batches:
    #             ##################### update G #####################
    #             gen_iterations += 1                
    #             self.set_requires_grad_value(netsD[0], False)
    #             self.set_requires_grad_value(netsD[1], False)
    #             self.set_requires_grad_value(netsD[2], False)
    #             netG.zero_grad()
    #             noise.data.normal_(0, 1)
    #             noise.requires_grad_(True)
    #             step +=1
    #             data = data_iter.next()
    #             imgs, captions, cap_lens, class_ids, keys = prepare_data(data)
    #             hidden = text_encoder.init_hidden(batch_size)
    #             words_embs, sent_emb = text_encoder(captions, cap_lens, hidden)
    #             words_embs, sent_emb = words_embs.detach(), sent_emb.detach()
    #             mask = (captions == 0)
    #             num_words = words_embs.size(2)
    #             if mask.size(1) > num_words:
    #                 mask = mask[:, :num_words]
    #             fake_imgs, _, mu, logvar = netG(noise, sent_emb, words_embs, mask)
    #             errG_total, G_logs = \
    #                 generator_loss_halfWGAN(netsD, image_encoder, fake_imgs, real_labels,
    #                                words_embs, sent_emb, match_labels, cap_lens, class_ids)
    #             kl_loss = KL_loss(mu, logvar)
    #             errG_total += kl_loss
    #             G_logs += 'kl_loss: %.2f ' % kl_loss.item()
    #             # backward and update parameters
    #             errG_total.backward()
    #             optimizerG.step()
    #             for p, avg_p in zip(netG.parameters(), avg_param_G):
    #                 avg_p.mul_(0.999).add_(0.001, p.data)
    #             ########################### update D ############################
    #             self.set_requires_grad_value(netsD[0], True)
    #             self.set_requires_grad_value(netsD[1], True)
    #             self.set_requires_grad_value(netsD[2], True)
    #             for d_iter in range(self.critic):
    #                 step +=1
    #                 data = data_iter.next()
    #                 imgs, captions, cap_lens, class_ids, keys = prepare_data(data)
    #                 hidden = text_encoder.init_hidden(batch_size)
    #                 words_embs, sent_emb = text_encoder(captions, cap_lens, hidden)
    #                 words_embs, sent_emb = words_embs.detach(), sent_emb.detach()
    #                 mask = (captions == 0)
    #                 num_words = words_embs.size(2)
    #                 if mask.size(1) > num_words:
    #                     mask = mask[:, :num_words]
    #                 #######################################################
    #                 # (2) Generate fake images
    #                 ######################################################
    #                 noise.data.normal_(0, 1)
    #                 fake_imgs, _, mu, logvar = netG(noise, sent_emb, words_embs, mask)
    #                 #######################################################
    #                 # (3) Update D network
    #                 ######################################################
    #                 errD_total = 0
    #                 nopenal = 0
    #                 D_logs = ''
    #                 for i in range(len(netsD)):
    #                     netsD[i].zero_grad() 
    #                     errD , gradient_penalty= discriminator_loss_halfWGAN(netsD[i], \
    #                         imgs[i], fake_imgs[i],sent_emb, real_labels, fake_labels)         

    #                     gradient_penalty.backward(retain_graph=True)
    #                     errD.backward()
    #                     optimizersD[i].step()
    #                     errD_total += errD + gradient_penalty
    #                     nopenal += errD
    #                     D_logs += 'errD%d: %.2f ' % (i, errD.item())
    #                     D_logs += 'penalty%d: %.2f ' % (i, gradient_penalty.item())

    #             if gen_iterations % 100 == 0:
    #                 print(D_logs + '\n' + G_logs)
    #             # save images
    #             if gen_iterations % 500 == 0:
    #                 self.save_img_results(netG, fixed_noise, sent_emb,
    #                                       words_embs, mask, image_encoder,
    #                                       captions, cap_lens, epoch, name='average')
                    
    #         end_t = time.time()
    #         print('''[%d/%d][%d]
    #               critic loss no penalty: %.2f ; with penalty: %.2f ; Loss_G012: %.2f Time: %.2fs'''
    #               % (epoch, self.max_epoch,self.num_batches,
    #                  nopenal.item(), errD_total.item(), errG_total.item(),
    #                  end_t - start_t))

    #         if epoch % cfg.WGAN.SNAPSHOT_INTERVAL == 0:  # and epoch != 0:
    #             print('check point save in epoch ', epoch)
    #             self.save_model(netG, avg_param_G, netsD, epoch)
    #             print('-'*80)


    #     self.save_model(netG, avg_param_G, netsD, self.max_epoch)


    def train(self):
        text_encoder, image_encoder, netG, netsD, start_epoch = self.build_models()
        avg_param_G = copy_G_params(netG)
        optimizerG, optimizersD = self.define_optimizers(netG, netsD)

        # schedulerG = optim.lr_scheduler.StepLR(optimizerG, step_size=100, gamma=0.1)
        # schedulerD0 = optim.lr_scheduler.StepLR(optimizersD[0], step_size=100, gamma=0.1)
        # schedulerD1 = optim.lr_scheduler.StepLR(optimizersD[1], step_size=100, gamma=0.5)
        # schedulerD2 = optim.lr_scheduler.StepLR(optimizersD[2], step_size=100, gamma=0.5)
        # print("using scheduler")

        real_labels, fake_labels, match_labels = self.prepare_labels()

        batch_size = self.batch_size
        nz = cfg.GAN.Z_DIM
        noise = Variable(torch.FloatTensor(batch_size, nz))
        fixed_noise = Variable(torch.FloatTensor(batch_size, nz).normal_(0, 1))
        if cfg.CUDA:
            noise, fixed_noise = noise.cuda(), fixed_noise.cuda()
        gen_iterations = 0
        
 

        print('')
        print('WGAN generator training %d epoch, batch size is %d, %d number of batches per epoch, \
            models saved every %d epoch' % (self.max_epoch,self.batch_size,self.num_batches, cfg.WGAN.SNAPSHOT_INTERVAL))
        print('')

        for epoch in range(start_epoch, self.max_epoch):

            # schedulerG.step()
            # schedulerD0.step()
            # schedulerD1.step()
            # schedulerD2.step()

            start_t = time.time()
            data_iter = iter(self.data_loader)
            step = 0

            ##      ##.         one epoch  ##            ##

            while (step+self.critic+1) < self.num_batches:



                ##################### update G #####################
                gen_iterations += 1
                
                self.set_requires_grad_value(netsD[0], False)
                self.set_requires_grad_value(netsD[1], False)
                self.set_requires_grad_value(netsD[2], False)
                
                netG.zero_grad()

                noise.data.normal_(0, 1)
                noise.requires_grad_(True)

                step +=1
                data = data_iter.next()

                imgs, captions, cap_lens, class_ids, keys = prepare_data(data)
                hidden = text_encoder.init_hidden(batch_size)
                # words_embs: batch_size x nef x seq_len
                # sent_emb: batch_size x nef
                words_embs, sent_emb = text_encoder(captions, cap_lens, hidden)
                words_embs, sent_emb = words_embs.detach(), sent_emb.detach()
                mask = (captions == 0)
                num_words = words_embs.size(2)
                if mask.size(1) > num_words:
                    mask = mask[:, :num_words]

                fake_imgs, _, mu, logvar = netG(noise, sent_emb, words_embs, mask)

                errG_0, errG_total, G_logs = \
                    generator_loss_WGAN_epoch(netsD, image_encoder, fake_imgs, real_labels,
                                   words_embs, sent_emb, match_labels, cap_lens, class_ids)
               

                kl_loss = KL_loss(mu, logvar)
                errG_total += kl_loss
                G_logs += 'kl_loss: %.2f ' % kl_loss.item()
                # backward and update parameters
                errG_0.backward(retain_graph=True)
                errG_total.backward()
                

                optimizerG.step()

                for p, avg_p in zip(netG.parameters(), avg_param_G):
                    avg_p.mul_(0.999).add_(0.001, p.data)



                ########################### update D ############################

                self.set_requires_grad_value(netsD[0], True)
                self.set_requires_grad_value(netsD[1], True)
                self.set_requires_grad_value(netsD[2], True)


                for d_iter in range(self.critic):
                    step +=1
                    data = data_iter.next()

                    imgs, captions, cap_lens, class_ids, keys = prepare_data(data)
                    hidden = text_encoder.init_hidden(batch_size)
                    # words_embs: batch_size x nef x seq_len
                    # sent_emb: batch_size x nef
                    words_embs, sent_emb = text_encoder(captions, cap_lens, hidden)
                    words_embs, sent_emb = words_embs.detach(), sent_emb.detach()
                    mask = (captions == 0)
                    num_words = words_embs.size(2)
                    if mask.size(1) > num_words:
                        mask = mask[:, :num_words]

                    #######################################################
                    # (2) Generate fake images
                    ######################################################
                    noise.data.normal_(0, 1)
                    fake_imgs, _, mu, logvar = netG(noise, sent_emb, words_embs, mask)

                    #######################################################
                    # (3) Update D network
                    ######################################################
                    errD_total = 0
                    D_logs = ''
                    for i in range(len(netsD)):
                        netsD[i].zero_grad() 
                        if i == 0:
                           

                            errD , gradient_penalty= discriminator_loss_WGAN(netsD[i], \
                                imgs[i], fake_imgs[i],sent_emb, real_labels, fake_labels)         

                            gradient_penalty.backward(retain_graph=True)
                            errD.backward()
                            optimizersD[i].step()
                            errD_total += errD + gradient_penalty
                            D_logs += 'errD%d: %.2f ' % (i, errD_total.item())
                        else:
                            errD = discriminator_loss(netsD[i], imgs[i], fake_imgs[i],
                                              sent_emb, real_labels, fake_labels)
                            errD.backward()
                            optimizersD[i].step()
                            errD_total += errD

                            D_logs += 'errD%d: %.2f ' % (i, errD.item())
                        
                    # Wasserstein_D = cond_real_errD - cond_fake_errD
                    



                if gen_iterations % 100 == 0:
                    print(D_logs + '\n' + G_logs)
                # save images
                if gen_iterations % 500 == 0:
                    # backup_para = copy_G_params(netG)
                    # load_params(netG, avg_param_G)
                    self.save_img_results(netG, fixed_noise, sent_emb,
                                          words_embs, mask, image_encoder,
                                          captions, cap_lens, epoch, name='average')
                    # load_params(netG, backup_para)
                    

            end_t = time.time()

            print('''[%d/%d][%d]
                  critic loss no penalty: %.2f ; with penalty: %.2f ; Loss_G0: %.2f;Loss_G12: %.2f Time: %.2fs'''
                  % (epoch, self.max_epoch,self.num_batches,
                     errD.item(), errD_total.item(), errG_0.item(), errG_total.item(),
                     end_t - start_t))

            if epoch % cfg.WGAN.SNAPSHOT_INTERVAL == 0:  # and epoch != 0:
                print('check point save in epoch ', epoch)
                self.save_model(netG, avg_param_G, netsD, epoch)
                print('-'*80)


        self.save_model(netG, avg_param_G, netsD, self.max_epoch)



    def save_singleimages(self, images, filenames, save_dir,
                          split_dir, sentenceID=0):
        for i in range(images.size(0)):
            s_tmp = '%s/single_samples/%s/%s' %\
                (save_dir, split_dir, filenames[i])
            folder = s_tmp[:s_tmp.rfind('/')]
            if not os.path.isdir(folder):
                print('Make a new folder: ', folder)
                mkdir_p(folder)

            fullpath = '%s_%d.jpg' % (s_tmp, sentenceID)
            # range from [-1, 1] to [0, 1]
            # img = (images[i] + 1.0) / 2
            img = images[i].add(1).div(2).mul(255).clamp(0, 255).byte()
            # range from [0, 1] to [0, 255]
            ndarr = img.permute(1, 2, 0).data.cpu().numpy()
            im = Image.fromarray(ndarr)
            im.save(fullpath)

    def sampling(self, split_dir):
        if cfg.TRAIN.NET_G == '':
            print('Error: the path for morels is not found!')
        else:
            if split_dir == 'test':
                split_dir = 'valid'
            # Build and load the generator
            if cfg.GAN.B_DCGAN:
                netG = G_DCGAN()
            else:
                netG = G_NET()
            netG.apply(weights_init)
            netG.cuda()
            netG.eval()
            #
            text_encoder = RNN_ENCODER(self.n_words, nhidden=cfg.TEXT.EMBEDDING_DIM)
            state_dict = \
                torch.load(cfg.TRAIN.NET_E, map_location=lambda storage, loc: storage)
            text_encoder.load_state_dict(state_dict)
            print('Load text encoder from:', cfg.TRAIN.NET_E)
            text_encoder = text_encoder.cuda()
            text_encoder.eval()

            batch_size = self.batch_size
            nz = cfg.GAN.Z_DIM
            noise = Variable(torch.FloatTensor(batch_size, nz), volatile=True)
            noise = noise.cuda()

            model_dir = cfg.TRAIN.NET_G
            state_dict = \
                torch.load(model_dir, map_location=lambda storage, loc: storage)
            # state_dict = torch.load(cfg.TRAIN.NET_G)
            netG.load_state_dict(state_dict)
            print('Load G from: ', model_dir)

            # the path to save generated images
            s_tmp = model_dir[:model_dir.rfind('.pth')]
            save_dir = '%s/%s' % (s_tmp, split_dir)
            mkdir_p(save_dir)

            cnt = 0

            for _ in range(1):  # (cfg.TEXT.CAPTIONS_PER_IMAGE):
                for step, data in enumerate(self.data_loader, 0):
                    cnt += batch_size
                    if step % 100 == 0:
                        print('step: ', step)
                    # if step > 50:
                    #     break

                    imgs, captions, cap_lens, class_ids, keys = prepare_data(data)

                    hidden = text_encoder.init_hidden(batch_size)
                    # words_embs: batch_size x nef x seq_len
                    # sent_emb: batch_size x nef
                    words_embs, sent_emb = text_encoder(captions, cap_lens, hidden)
                    words_embs, sent_emb = words_embs.detach(), sent_emb.detach()
                    mask = (captions == 0)
                    num_words = words_embs.size(2)
                    if mask.size(1) > num_words:
                        mask = mask[:, :num_words]

                    #######################################################
                    # (2) Generate fake images
                    ######################################################
                    noise.data.normal_(0, 1)
                    fake_imgs, _, _, _ = netG(noise, sent_emb, words_embs, mask)
                    for j in range(batch_size):
                        s_tmp = '%s/single/%s' % (save_dir, keys[j])
                        folder = s_tmp[:s_tmp.rfind('/')]
                        if not os.path.isdir(folder):
                            print('Make a new folder: ', folder)
                            mkdir_p(folder)
                        k = -1
                        # for k in range(len(fake_imgs)):
                        im = fake_imgs[k][j].data.cpu().numpy()
                        # [-1, 1] --> [0, 255]
                        im = (im + 1.0) * 127.5
                        im = im.astype(np.uint8)
                        im = np.transpose(im, (1, 2, 0))
                        im = Image.fromarray(im)
                        fullpath = '%s_s%d.png' % (s_tmp, k)
                        im.save(fullpath)

        print('-'*80)
        print('sampling images saved to ', fullpath)
        print('-'*80)

    def gen_example(self, data_dic):
        if cfg.TRAIN.NET_G == '':
            print('Error: the path for morels is not found!')
        else:
            # Build and load the generator
            text_encoder = \
                RNN_ENCODER(self.n_words, nhidden=cfg.TEXT.EMBEDDING_DIM)
            state_dict = \
                torch.load(cfg.TRAIN.NET_E, map_location=lambda storage, loc: storage)
            text_encoder.load_state_dict(state_dict)
            print('-'*80)
            print('Load text encoder from:', cfg.TRAIN.NET_E)

            text_encoder = text_encoder.cuda()
            text_encoder.eval()

            # the path to save generated images
            if cfg.GAN.B_DCGAN:
                netG = G_DCGAN()
            else:
                netG = G_NET()


            # s_tmp = cfg.TRAIN.NET_G[:cfg.TRAIN.NET_G.rfind('.pth')]
            s_tmp = '../models/bird_AttnWGAN'



            model_dir = cfg.TRAIN.NET_G
            state_dict = \
                torch.load(model_dir, map_location=lambda storage, loc: storage)
            netG.load_state_dict(state_dict)
            print('Load G from: ', model_dir)
            print('-'*80)
            netG.cuda()
            netG.eval()

         

            for key in data_dic:
                save_dir = '%s/%s' % (s_tmp, key)
                mkdir_p(save_dir)

                captions, cap_lens, sorted_indices = data_dic[key]

                batch_size = captions.shape[0]

                
                nz = cfg.GAN.Z_DIM
                captions = Variable(torch.from_numpy(captions), volatile=True)
                cap_lens = Variable(torch.from_numpy(cap_lens), volatile=True)

                captions = captions.cuda()
                cap_lens = cap_lens.cuda()
                for i in range(1):  # 16
                    noise = Variable(torch.FloatTensor(batch_size, nz), volatile=True)
                    noise = noise.cuda()
                    #######################################################
                    # (1) Extract text embeddings
                    ######################################################
                    hidden = text_encoder.init_hidden(batch_size)
                    # words_embs: batch_size x nef x seq_len
                    # sent_emb: batch_size x nef
                    words_embs, sent_emb = text_encoder(captions, cap_lens, hidden)
                    mask = (captions == 0)
                    #######################################################
                    # (2) Generate fake images
                    ######################################################
                    noise.data.normal_(0, 1)
                    fake_imgs, attention_maps, _, _ = netG(noise, sent_emb, words_embs, mask)
                    # G attention
                    cap_lens_np = cap_lens.cpu().data.numpy()

                    for j in range(batch_size):
                        save_name = '%s/%d_s_%d' % (save_dir, i, sorted_indices[j])
                        for k in range(len(fake_imgs)):
                            im = fake_imgs[k][j].data.cpu().numpy()
                            im = (im + 1.0) * 127.5
                            im = im.astype(np.uint8)
                            # print('im', im.shape)
                            im = np.transpose(im, (1, 2, 0))
                            # print('im', im.shape)
                            im = Image.fromarray(im)
                            fullpath = '%s_g%d.png' % (save_name, k)
                            im.save(fullpath)

                        for k in range(len(attention_maps)):
                            if len(fake_imgs) > 1:
                                im = fake_imgs[k + 1].detach().cpu()
                            else:
                                im = fake_imgs[0].detach().cpu()
                            attn_maps = attention_maps[k]
                            att_sze = attn_maps.size(2)
                            img_set, sentences = \
                                build_super_images2(im[j].unsqueeze(0),
                                                    captions[j].unsqueeze(0),
                                                    [cap_lens_np[j]], self.ixtoword,
                                                    [attn_maps[j]], att_sze)
                            if img_set is not None:
                                im = Image.fromarray(img_set)
                                fullpath = '%s_a%d.png' % (save_name, k)
                                im.save(fullpath)

            print('-'*80)
            print('save generated image to: ',fullpath)
            print('-'*80)
